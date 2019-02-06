import java.io.File;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.CyclicBarrier;
import java.util.function.Predicate;

import com.google.common.collect.BiMap;
import com.google.common.collect.HashBiMap;

import com.univocity.parsers.csv.CsvWriter;
import com.univocity.parsers.csv.CsvWriterSettings;

public class Sample {

	private static final String SIMILARITY_MEASURE = "sim_cs";
	private static final double LAMBDA = 0.6; // Parameter for MMR
	private static final double RAND_PCT = 0.00; // Percentage of randomly chosen elements
	private static final double SIM_THRSH = 0.01; // Used to save memory
	private static final double SIM_TOK_IP = 0.75; // Interpolation of sim and sim_tok

	private static final Random rng = new Random();
	private static long startTime;

	private static Worker[] workers = null;
	private static CyclicBarrier barrier;

	private static final BiMap<String, Integer> stringCache = HashBiMap.create();
	private static final BiMap<Integer, String> idToString = stringCache.inverse();



	private static class Pair {
		public final int file1;
		public final int method1;
		public final int file2;
		public final int method2;

		Pair(final String file1, final String method1, final String file2, final String method2) {
			this.file1 = stringCache.computeIfAbsent(file1, key -> stringCache.size());
			this.method1 = stringCache.computeIfAbsent(method1, key -> stringCache.size());
			this.file2 = stringCache.computeIfAbsent(file2, key -> stringCache.size());
			this.method2 = stringCache.computeIfAbsent(method2, key -> stringCache.size());
		}

		@Override
		public boolean equals(final Object obj) {
			if (obj instanceof Pair) {
				final Pair other = (Pair) obj;
				return this.file1 == other.file1
						&& this.method1 == other.method1
						&& this.file2 == other.file2
						&& this.method2 == other.method2;
			}
			return false;
		}

		@Override
		public int hashCode() {
			return Objects.hash(this.file1, this.method1, this.file2, this.method2);
		}
	}



	private static class SimPair extends Pair {
		public final int project1;
		public final int project2;
		public final double sim;
		public final double tokenSim;

		SimPair(final String project1, final String file1, final String method1,
				final String project2, final String file2, final String method2, final double sim,
				final double tokenSim) {

			super(file1, method1, file2, method2);

			this.project1 = stringCache.computeIfAbsent(project1, key -> stringCache.size());
			this.project2 = stringCache.computeIfAbsent(project2, key -> stringCache.size());
			this.sim = sim;
			this.tokenSim = tokenSim;
		}

		private double getCombinedSim() {
			return SIM_TOK_IP * this.sim + (1.0 - SIM_TOK_IP) * (1.0 - this.tokenSim);
		}
	}



	private static class Worker extends Thread {

		private final int id;
		private final int threadCount;
		private final CyclicBarrier barrier;

		public List<SimPair> datasetList;
		public Map<Pair, Double> datasetMap;
		public Set<SimPair> selected;

		public double bestSim;
		public List<SimPair> best;

		Worker(final int id, final int threadCount, final CyclicBarrier barrier) {
			this.id = id;
			this.threadCount = threadCount;
			this.barrier = barrier;
		}

		@Override
		public void run() {
			try {
				while (true) {
					barrier.await();

					this.bestSim = Double.NEGATIVE_INFINITY;
					this.best = null;

					for (int i = this.id; i < this.datasetList.size(); i += this.threadCount) {
						final SimPair item = this.datasetList.get(i);

						if (item.getCombinedSim() < this.bestSim) {
							break;
						}

						if (!selected.contains(item)) {
							final double curSim = LAMBDA * item.getCombinedSim()
									- (1.0 - LAMBDA) * getMaxSelSim(item, datasetMap, selected);
							if (curSim > this.bestSim) {
								this.bestSim = curSim;
								this.best = new ArrayList<>();
								this.best.add(item);
							} else if (curSim == this.bestSim) {
								this.best.add(item);
							}
						}
					}

					barrier.await();
				}
			} catch (Exception e) {
				e.printStackTrace();
			}
		}
	}



	private static void beginTimeMeasurement() {
		startTime = System.currentTimeMillis();
	}



	private static void endTimeMeasurement(final String name) {
		System.out.printf("%s in %.2f s%n", name, (System.currentTimeMillis() - startTime) / 1000.0);
	}



	private static boolean projFilter(final String project) {
		return !"jEdit".equals(project);
	}



	private static boolean fnameFilter(final String fname) {
		return !fname.contains("/example/") && !fname.contains("/examples/")
				&& !fname.contains("/android/") && !fname.matches(".*/test[0-9]+/.*");
	}



	private static boolean filterFunc(final SimPair pair) {
		return projFilter(idToString.get(pair.project1)) && projFilter(idToString.get(pair.project2))
				&& fnameFilter(idToString.get(pair.file1)) && fnameFilter(idToString.get(pair.file2));
	}



	private static boolean isLessThan(final String file1, final String method1, final String file2,
			final String method2) {

		final int fileCmp = file1.compareTo(file2);
		if (fileCmp != 0) {
			return fileCmp < 0;
		}
		return method1.compareTo(method2) < 0;
	}



	private static List<SimPair> getDatasetList(final Statement stmt,
			final Predicate<SimPair> filterFunc) throws SQLException {

		final ResultSet countSet = stmt.executeQuery(
				"SELECT count(*) FROM internal_methodsim WHERE " + SIMILARITY_MEASURE + " > " + SIM_THRSH);
		if (!countSet.next()) {
			throw new IllegalStateException();
		}
		final int count = countSet.getInt(1);
		countSet.close();

		final ResultSet resultSet = stmt.executeQuery(
				"SELECT project1, file1, method1, project2, file2, method2, " + SIMILARITY_MEASURE
				+ " AS sim, sim_tok FROM methodsim WHERE sim > " + SIM_THRSH
				+ " ORDER BY sim DESC");

		final List<SimPair> result = new ArrayList<>(count);
		while (resultSet.next()) {
			final SimPair pair = new SimPair(
					resultSet.getString(1), resultSet.getString(2), resultSet.getString(3),
					resultSet.getString(4), resultSet.getString(5), resultSet.getString(6),
					resultSet.getDouble(7), resultSet.getDouble(8));

			if (filterFunc.test(pair)) {
				result.add(pair);
			}
		}

		resultSet.close();

		return result;
	}



	private static SimPair selectInitial(final List<SimPair> datasetList) {
		int i = 0;
		final double init = datasetList.get(0).getCombinedSim();
		for (; i < datasetList.size() && datasetList.get(i).getCombinedSim() >= init; ++i) { }
		return datasetList.get(rng.nextInt(i));
	}



	private static double sigmoid(final double x) {
		return 2.0 / (1.0 + Math.exp(-x)) - 1.0;
	}



	private static double getSim(final Map<Pair, Double> datasetMap, final int file1,
			final int method1, final int file2, final int method2) {

		return getSim(datasetMap, idToString.get(file1), idToString.get(method1),
				idToString.get(file2), idToString.get(method2));
	}



	private static double getSim(final Map<Pair, Double> datasetMap, final String file1,
			final String method1, final String file2, final String method2) {

		if (file1.equals(file2) && method1.equals(method2)) {
			return 1;
		}
		if (isLessThan(file1, method1, file2, method2)) {
			return datasetMap.getOrDefault(new Pair(file1, method1, file2, method2), 0.0);
		} else {
			return datasetMap.getOrDefault(new Pair(file2, method2, file1, method1), 0.0);
		}
	}



	private static double getMaxSelSim(final SimPair item,
			final Map<Pair, Double> datasetMap, final Set<SimPair> selected) {

		double projSim = 0.0;
		double fileSim = 0.0;
		for (final SimPair sel : selected) {
			if (sel.project1 == item.project1 && sel.project2 == item.project2) {
				projSim += 1.0;
			}
			if (sel.file1 == item.file1) {
				fileSim += 1.0;
			}
			if (sel.file2 == item.file2) {
				fileSim += 1.0;
			}
		}
		projSim /= selected.size();
		fileSim /= selected.size();

		double bestSim = Double.NEGATIVE_INFINITY;
		for (final SimPair sel : selected) {
			final double curSim = sigmoid(
					getSim(datasetMap, item.file1, item.method1, sel.file1, sel.method1)
					+ getSim(datasetMap, item.file1, item.method1, sel.file2, sel.method2)
					+ getSim(datasetMap, item.file2, item.method2, sel.file1, sel.method1)
					+ getSim(datasetMap, item.file2, item.method2, sel.file2, sel.method2)
					+ projSim
					+ fileSim);
			if (curSim > bestSim) {
				bestSim = curSim;
			}
		}
		return bestSim;
	}



	private static SimPair selectMMR(final List<SimPair> datasetList,
			final Map<Pair, Double> datasetMap, final Set<SimPair> selected) {

		double bestSim = Double.NEGATIVE_INFINITY;
		List<SimPair> best = null;
		for (final SimPair item : datasetList) {
			if (item.getCombinedSim() < bestSim) {
				break;
			}

			if (!selected.contains(item)) {
				final double curSim = LAMBDA * item.getCombinedSim()
						- (1.0 - LAMBDA) * getMaxSelSim(item, datasetMap, selected);
				if (curSim > bestSim) {
					bestSim = curSim;
					best = new ArrayList<>();
					best.add(item);
				} else if (curSim == bestSim) {
					best.add(item);
				}
			}
		}

		if (best == null) {
			return null;
		} else {
			return best.get(rng.nextInt(best.size()));
		}
	}



	private static SimPair selectMMRParallel(final List<SimPair> datasetList,
			final Map<Pair, Double> datasetMap, final Set<SimPair> selected) {

		if (workers == null) {
			final int threadCount = Runtime.getRuntime().availableProcessors();
			workers = new Worker[threadCount];
			barrier = new CyclicBarrier(threadCount + 1);

			for (int i = 0; i < threadCount; ++i) {
				workers[i] = new Worker(i, threadCount, barrier);
				workers[i].setDaemon(true);
				workers[i].start();
			}
		}

		for (int i = 0; i < workers.length; ++i) {
			workers[i].datasetList = datasetList;
			workers[i].datasetMap = datasetMap;
			workers[i].selected = selected;
		}

		try {
			barrier.await();
			barrier.await();
		} catch (final Exception e) {
			e.printStackTrace();
		}

		double bestSim = Double.NEGATIVE_INFINITY;
		List<SimPair> best = null;

		for (final Worker w : workers) {
			if (w.bestSim > bestSim) {
				bestSim = w.bestSim;
				best = w.best;
			} else if (w.bestSim == bestSim && w.best != null) {
				best.addAll(w.best);
			}
		}

		if (best == null) {
			return null;
		} else {
			return best.get(rng.nextInt(best.size()));
		}
	}



	private static void writeCsvOutput(final File outputFile, final List<SimPair> result,
			final Connection conn) throws SQLException {

		final CsvWriterSettings writerSettings = new CsvWriterSettings();
		final CsvWriter writer = new CsvWriter(outputFile, writerSettings);
		try {
			writer.writeHeaders("pairid", "ident1", "project1", "file1", "method1",
					"ident2", "project2", "file2", "method2", "sim", "sim_tok");

			int num = 0;

			for (final SimPair item : result) {
				final String file1 = idToString.get(item.file1);
				final String file2 = idToString.get(item.file2);
				final String method1 = idToString.get(item.method1);
				final String method2 = idToString.get(item.method2);

				final PreparedStatement pstmt1 = conn.prepareStatement(
						"SELECT id FROM internal_filtered_methoddocs WHERE file = ? AND method = ?");
				pstmt1.setString(1, file1);
				pstmt1.setString(2, method1);
				
				final ResultSet rs1 = pstmt1.executeQuery();
				rs1.next();
				final int ident1 = rs1.getInt("id");

				final PreparedStatement pstmt2 = conn.prepareStatement(
						"SELECT id FROM internal_filtered_methoddocs WHERE file = ? AND method = ?");
				pstmt2.setString(1, file2);
				pstmt2.setString(2, method2);
				
				final ResultSet rs2 = pstmt2.executeQuery();
				rs2.next();
				final int ident2 = rs2.getInt("id");

				writer.writeRow(num,
						ident1, idToString.get(item.project1), file1, method1,
						ident2, idToString.get(item.project2), file2, method2,
						item.sim, item.tokenSim);

				num += 1;
			}
		} finally {
			writer.close();
		}
	}



	public static void main(String[] args) {
		Class jdbc = org.sqlite.JDBC.class; // Ensure class is loaded

		final int count = Integer.parseInt(args[0]);
		final File outputFile = new File(args[1]);

		Connection conn = null;
		try {
			conn = DriverManager.getConnection("jdbc:sqlite:docs.db");
			try {
				final Statement stmt = conn.createStatement();

				beginTimeMeasurement();
				final List<SimPair> fullDatasetList = getDatasetList(stmt, Sample::filterFunc);
				endTimeMeasurement("Fetched dataset");

				final List<SimPair> result = new ArrayList<>();
				final Map<Pair, Double> datasetMap = new HashMap<>(fullDatasetList.size());
				final List<SimPair> datasetList = new ArrayList<>();

				beginTimeMeasurement();
				for (final SimPair pair : fullDatasetList) {
					final String file1 = idToString.get(pair.file1);
					final String file2 = idToString.get(pair.file2);
					final String method1 = idToString.get(pair.method1);
					final String method2 = idToString.get(pair.method2);

					if (isLessThan(file1, method1, file2, method2)) {
						datasetMap.put(pair, pair.getCombinedSim());
					} else {
						datasetMap.put(new Pair(file2, method2, file1, method1), pair.getCombinedSim());
					}
					if (pair.project1 != pair.project2) {
						datasetList.add(pair);
					}
				}
				endTimeMeasurement("Built map");

				final Set<SimPair> selected = new HashSet<>();

				beginTimeMeasurement();
				final SimPair initial = selectInitial(datasetList);
				result.add(initial);
				selected.add(initial);
				for (int i = 1; i < (int) (count * (1 - RAND_PCT)); ++i) {
					System.err.printf("\r%.2f%%", (double) result.size() * 100.0 / count);

					final SimPair nextItem = selectMMRParallel(datasetList, datasetMap, selected);
					result.add(nextItem);
					selected.add(nextItem);
				}
				
				while (result.size() < count) {
					System.err.printf("\r%.2f%%", (double) result.size() * 100.0 / count);

					final SimPair nextItem = datasetList.get(rng.nextInt(datasetList.size()));
					if (selected.add(nextItem)) {
						result.add(nextItem);
					}
				}
				System.err.println("\r100%  ");

				endTimeMeasurement("Selected items");

				beginTimeMeasurement();
				writeCsvOutput(outputFile, result, conn);
				endTimeMeasurement("Wrote output");
			} finally {
				conn.close();
			}
		} catch (SQLException e) {
			System.err.print("[E] ");
			System.err.println(e.getMessage());
			e.printStackTrace();
			System.exit(1);
		}
	}
}

