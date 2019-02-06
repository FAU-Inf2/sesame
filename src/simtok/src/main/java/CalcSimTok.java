import java.io.File;
import java.io.IOException;
import java.nio.charset.Charset;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ExecutionException;

import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.google.common.collect.ImmutableSet;

import org.apache.commons.io.FileUtils;

import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.core.ToolFactory;
import org.eclipse.jdt.core.dom.AbstractTypeDeclaration;
import org.eclipse.jdt.core.dom.AST;
import org.eclipse.jdt.core.dom.ASTParser;
import org.eclipse.jdt.core.dom.CompilationUnit;
import org.eclipse.jdt.core.dom.MethodDeclaration;
import org.eclipse.jdt.core.compiler.InvalidInputException;
import org.eclipse.jdt.core.compiler.IScanner;
import org.eclipse.jdt.core.compiler.ITerminalSymbols;

public class CalcSimTok {

	private static class Token {
		private final int tokenType;
		private final String tokenText;

		private Token(final int tokenType, final String tokenText) {
			this.tokenType = tokenType;
			this.tokenText = tokenText;
		}

		static Token fromScanner(final IScanner scanner, final Set<Integer> toIdentTokens)
				throws InvalidInputException {

			int tokenType = scanner.getNextToken();

			if (tokenType == ITerminalSymbols.TokenNameEOF) {
				return null;
			}

			if (toIdentTokens.contains(tokenType)) {
				return new Token(ITerminalSymbols.TokenNameIdentifier,
						new String(scanner.getCurrentTokenSource()));
			}

			if (tokenType == ITerminalSymbols.TokenNameIdentifier) {
				return new Token(tokenType, new String(scanner.getCurrentTokenSource()));
			} else {
				return new Token(tokenType, "");
			}
		}

		@Override
		public int hashCode() {
			return Objects.hash(this.tokenType, this.tokenText);
		}

		@Override
		public boolean equals(final Object obj) {
			if (obj instanceof Token) {
				final Token other = (Token) obj;
				return this.tokenType == other.tokenType;
						//&& (this.tokenType != ITerminalSymbols.TokenNameIdentifier
						//	|| this.tokenText.equals(other.tokenText));
			}
			return false;
		}

		@Override
		public String toString() {
			return String.valueOf(this.tokenType);
		}
	}



	public static void main(String[] args) {
		Class jdbc = org.sqlite.JDBC.class; // Ensure class is loaded

		Connection conn = null;
		try {
			conn = DriverManager.getConnection("jdbc:sqlite:docs.db");
			try {
				conn.setAutoCommit(false);

				final Statement stmt = conn.createStatement();

				int cachedTokensId = -1;
				List<Token> cachedTokens = null;
				final LoadingCache<Integer, List<Token>> tokenCache = CacheBuilder.newBuilder()
						.maximumSize(30000)
						.build(new CacheLoader<Integer, List<Token>>() {
							@Override
							public List<Token> load(final Integer id) throws SQLException, InvalidInputException {
								return tokenize(stmt, id);
							}
						});

				final ResultSet countSet = stmt.executeQuery(
						"SELECT count(*) FROM internal_methodsim");
				if (!countSet.next()) {
					throw new IllegalStateException();
				}
				final int count = countSet.getInt(1);
				countSet.close();

				int current = 0;
				final PreparedStatement updStmt = conn.prepareStatement(
						"UPDATE internal_methodsim SET sim_tok = ? WHERE first_id = ? AND second_id = ?");

				final Statement stmt2 = conn.createStatement();
				final ResultSet pairSet = stmt2.executeQuery(
						"SELECT first_id, second_id FROM internal_methodsim");

				final List<List<Object>> toProcess = new ArrayList<>();
				while (pairSet.next()) {
					final int firstId = pairSet.getInt(1);
					final int secondId = pairSet.getInt(2);

					try {
						final List<Token> firstTokens = cachedTokensId == firstId
								? cachedTokens
								: tokenCache.get(firstId);
						final List<Token> secondTokens = secondId == firstId
								? firstTokens
								: tokenCache.get(secondId);

						toProcess.add(Arrays.asList(firstId, secondId,
								tokenSimilarity(firstTokens, secondTokens)));

						cachedTokensId = firstId;
						cachedTokens = firstTokens;

						if ((current & 15) == 0) {
							System.out.printf("\r%.2f%% completed", (current * 100.0) / count);
						}
						current += 1;

						if (toProcess.size() >= 16384) {
							for (final List<Object> updRow : toProcess) {
								updStmt.setDouble(1, (Double) updRow.get(2));
								updStmt.setInt(2, (Integer) updRow.get(0));
								updStmt.setInt(3, (Integer) updRow.get(1));
								updStmt.addBatch();
							}
							updStmt.executeBatch();
							updStmt.clearBatch();
							toProcess.clear();
							conn.commit();
						}
					} catch (final ExecutionException e) {
						if (e.getCause() instanceof InvalidInputException) {
							current += 1;
						} else {
							throw (SQLException) e.getCause();
						}
					}
				}
				pairSet.close();

				for (final List<Object> updRow : toProcess) {
					updStmt.setDouble(1, (Double) updRow.get(2));
					updStmt.setInt(2, (Integer) updRow.get(0));
					updStmt.setInt(3, (Integer) updRow.get(1));
					updStmt.addBatch();
				}
				updStmt.executeBatch();
				conn.commit();
			} finally {
				conn.close();
			}
		} catch (SQLException e) {
			System.err.print("[E] ");
			System.err.println(e.getMessage());
			System.exit(1);
		}
	}



	private static List<Token> tokenize(final Statement stmt, final int id)
			throws SQLException, InvalidInputException {

		final ResultSet methodIdSet = stmt.executeQuery(
				"SELECT file, method FROM internal_filtered_methoddocs WHERE id = " + id);
		if (!methodIdSet.next()) {
			throw new IllegalStateException();
		}

		final String fileName = methodIdSet.getString(1);
		final String methodName = methodIdSet.getString(2);

		return tokenize(new File(fileName), methodName);
	}



	private static List<Token> tokenize(final File fileName, final String methodName)
			throws InvalidInputException {

		final Set<Integer> toIdentToken = ImmutableSet.of(
				ITerminalSymbols.TokenNameboolean,
				ITerminalSymbols.TokenNamebyte,
				ITerminalSymbols.TokenNamechar,
				ITerminalSymbols.TokenNamedouble,
				ITerminalSymbols.TokenNamefloat,
				ITerminalSymbols.TokenNameint,
				ITerminalSymbols.TokenNamelong,
				ITerminalSymbols.TokenNameshort);

		try {
			final char[] contentsArray = FileUtils
					.readFileToString(fileName, Charset.defaultCharset()).toCharArray();

			final ASTParser parser = ASTParser.newParser(AST.JLS10);
			parser.setSource(contentsArray);

			final Map options = JavaCore.getOptions();
			JavaCore.setComplianceOptions(JavaCore.VERSION_11, options);
			parser.setCompilerOptions(options);

			int startPos = -1;
			int endPos = -1;
			try {
				final CompilationUnit root = (CompilationUnit) parser.createAST(null);

				final MethodDeclaration methodDecl = Util.matchFunction(methodName,
						(List<AbstractTypeDeclaration>) root.types());

				startPos = methodDecl.getBody().getStartPosition();
				endPos = startPos + methodDecl.getBody().getLength();
			} catch (final IllegalArgumentException e) {
				throw new IllegalStateException("Cannot parse " + fileName, e);
			}

			final IScanner scanner = ToolFactory.createScanner(false, false, false, "1.8", "1.8");
			scanner.setSource(contentsArray);
			scanner.resetTo(startPos, endPos);

			final List<Token> result = new ArrayList<>();
			Token nextToken = null;
			while ((nextToken = Token.fromScanner(scanner, toIdentToken)) != null) {
				result.add(nextToken);
			}
			return result;
		} catch (final IOException e) {
			e.printStackTrace();
			System.exit(2);
			return null;
		}
	}



	private static double tokenSimilarity(final List<Token> first, final List<Token> second) {
		return 1.0 - (double) levenshteinDistance(first, second) / Math.max(first.size(), second.size());
	}



	private static int levenshteinDistance(final List<Token> first, final List<Token> second) {
		if (first == second) {
			return 0;
		}

		final int size1 = first.size();
		final int size2 = second.size();

		if (size1 == 0) {
			return size2;
		}
		if (size2 == 0) {
			return size1;
		}

		int[] v0 = new int[size2 + 1];
		int[] v1 = new int[size2 + 1];

		for (int i = 0; i < v0.length; ++i) {
			v0[i] = i;
		}

		for (int i = 0; i < size1; ++i) {
			v1[0] = i + 1;

			for (int j = 0; j < size2; ++j) {
				v1[j + 1] = Math.min(v1[j] + 1,
						Math.min(v0[j + 1] + 1, v0[j] + (first.get(i).equals(second.get(j)) ? 0 : 1)));
			}

			final int[] temp = v0;
			v0 = v1;
			v1 = temp;
		}

		assert v0[size2] >= Math.max(size1, size2) - Math.min(size1, size2);

		return v0[size2];
	}
}

