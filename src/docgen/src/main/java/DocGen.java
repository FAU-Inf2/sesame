import java.io.File;
import java.io.IOException;
import java.nio.charset.Charset;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayDeque;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.StringJoiner;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.commons.io.FileUtils;
import org.apache.commons.text.StringEscapeUtils;

import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.core.dom.AbstractTypeDeclaration;
import org.eclipse.jdt.core.dom.AnnotationTypeDeclaration;
import org.eclipse.jdt.core.dom.AnonymousClassDeclaration;
import org.eclipse.jdt.core.dom.ArrayType;
import org.eclipse.jdt.core.dom.AST;
import org.eclipse.jdt.core.dom.ASTNode;
import org.eclipse.jdt.core.dom.ASTParser;
import org.eclipse.jdt.core.dom.ASTVisitor;
import org.eclipse.jdt.core.dom.CompilationUnit;
import org.eclipse.jdt.core.dom.ConditionalExpression;
import org.eclipse.jdt.core.dom.EnumConstantDeclaration;
import org.eclipse.jdt.core.dom.EnumDeclaration;
import org.eclipse.jdt.core.dom.FieldDeclaration;
import org.eclipse.jdt.core.dom.IDocElement;
import org.eclipse.jdt.core.dom.ImportDeclaration;
import org.eclipse.jdt.core.dom.InfixExpression;
import org.eclipse.jdt.core.dom.MemberRef;
import org.eclipse.jdt.core.dom.MethodDeclaration;
import org.eclipse.jdt.core.dom.MethodRef;
import org.eclipse.jdt.core.dom.Modifier;
import org.eclipse.jdt.core.dom.Name;
import org.eclipse.jdt.core.dom.NameQualifiedType;
import org.eclipse.jdt.core.dom.PackageDeclaration;
import org.eclipse.jdt.core.dom.ParameterizedType;
import org.eclipse.jdt.core.dom.PrimitiveType;
import org.eclipse.jdt.core.dom.QualifiedType;
import org.eclipse.jdt.core.dom.SimpleType;
import org.eclipse.jdt.core.dom.SingleVariableDeclaration;
import org.eclipse.jdt.core.dom.TagElement;
import org.eclipse.jdt.core.dom.TextElement;
import org.eclipse.jdt.core.dom.ThrowStatement;
import org.eclipse.jdt.core.dom.Type;
import org.eclipse.jdt.core.dom.TypeDeclaration;
import org.eclipse.jdt.core.dom.WildcardType;



public class DocGen {

	private static final Pattern DO_NOT_CONVERT_TO_LOWER = Pattern.compile(".+[A-Z].*");
	private static final Pattern TF_NOT1  = Pattern.compile("(\\w+)'nt");
	private static final Pattern TF_NOT2  = Pattern.compile("^(?!wo|ca)(\\w+)n't");
	private static final Pattern TF_ARE   = Pattern.compile("(\\w+)'re");
	private static final Pattern TF_WILL  = Pattern.compile("(\\w+)'ll");
	private static final Pattern TF_HAVE  = Pattern.compile("(\\w+)'ve");
	private static final Pattern TF_WOULD = Pattern.compile("(i|you|he|she|it|we|they)'d");


	private static int astNodeThreshold = 10;
	private static boolean fileFilter = true;


	private static PreparedStatement docStmt;
	private static int currentProjectId;
	private static int currentId;



	static {
		final String thresholdVal = System.getProperty("threshold");
		if (thresholdVal != null) {
			try {
				astNodeThreshold = Integer.parseInt(thresholdVal);
			} catch (final NumberFormatException e) { }
		}
		final String filterVal = System.getProperty("filter");
		fileFilter = !"false".equals(filterVal); // Invalid -> true
	}



	private static class MethodDocGeneratorVisitor extends ASTVisitor {

		private final ArrayDeque<String> enclosingClasses = new ArrayDeque<>();
		private final File file;


		MethodDocGeneratorVisitor(final File file) {
			this.file = file;
		}


		private void addClassName(final String name) {
			this.enclosingClasses.offerLast(name);
		}


		private void removeLastClassName() {
			this.enclosingClasses.pollLast();
		}


		private String getQualifiedName() {
			final StringJoiner joiner = new StringJoiner(".");
			for (final String className : this.enclosingClasses) {
				joiner.add(className);
			}
			return joiner.toString();
		}


		private boolean handleType(final AbstractTypeDeclaration decl) {
			addClassName(decl.getName().getIdentifier());

			if ((decl.getModifiers() & Modifier.PRIVATE) != 0) {
				// Skip private classes
				return false;
			}
			if (decl.getJavadoc() != null) {
				// Check that JavaDoc of type does not contain a "@test" tag
				// -> openjdk test
				for (final TagElement tag : ((List<TagElement>) decl.getJavadoc().tags())) {
					if ("@test".equals(tag.getTagName())) {
						return false;
					}
				}
				if (fileFilter && isInTestDirectory(this.file)) {
					// Check if class JavaDoc starts with the word "Test"
					if (!decl.getJavadoc().tags().isEmpty()) {
						final TagElement tag = (TagElement) decl.getJavadoc().tags().get(0);
						if (tag.getTagName() == null && !tag.fragments().isEmpty()
								&& tag.fragments().get(0) instanceof TextElement) {
							final TextElement txtElem = (TextElement) tag.fragments().get(0);
							if (txtElem.getText().startsWith("Test ")) {
								return false;
							}
						}
					}
				}
			}
			return true;
		}


		@Override
		public boolean visit(final AnnotationTypeDeclaration node) {
			return false;
		}


		@Override
		public boolean visit(final AnonymousClassDeclaration node) {
			return false;
		}


		@Override
		public boolean visit(final EnumConstantDeclaration node) {
			return false;
		}


		@Override
		public boolean visit(final EnumDeclaration node) {
			return handleType(node);
		}


		@Override
		public boolean visit(final FieldDeclaration node) {
			return false;
		}


		@Override
		public boolean visit(final ImportDeclaration node) {
			return false;
		}


		@Override
		public boolean visit(final MethodDeclaration node) {
			if (node.getJavadoc() != null && node.getBody() != null && !node.isConstructor()
					&& (node.getModifiers() & Modifier.PRIVATE) == 0
					&& (countNodes(node.getBody()) >= astNodeThreshold || hasInteresting(node.getBody()))
					&& (node.getBody().statements().size() > 1
						|| !(node.getBody().statements().get(0) instanceof ThrowStatement))) {

				handleMethodDocs(this.file,
						getQualifiedName(),
						getMethodName(node),
						(List<TagElement>) node.getJavadoc().tags());
			}
			return false;
		}


		@Override
		public boolean visit(final PackageDeclaration node) {
			return false;
		}


		@Override
		public boolean visit(final TypeDeclaration node) {
			return handleType(node);
		}


		@Override
		public void endVisit(final EnumDeclaration node) {
			removeLastClassName();
		}


		@Override
		public void endVisit(final TypeDeclaration node) {
			removeLastClassName();
		}
	}



	private static int countNodes(final ASTNode node) {
		final AtomicInteger counter = new AtomicInteger();
		node.accept(new ASTVisitor() {
			@Override
			public void preVisit(final ASTNode node) {
				counter.incrementAndGet();
			}
		});
		return counter.get();
	}



	private static boolean hasInteresting(final ASTNode node) {
		final AtomicBoolean result = new AtomicBoolean();
		node.accept(new ASTVisitor() {
			@Override
			public void endVisit(final ConditionalExpression node) {
				result.set(true);
			}

			@Override
			public void endVisit(final InfixExpression node) {
				result.set(true);
			}
		});
		return result.get();
	}



	private static void buildTypeString(final StringBuilder resultBuilder, final Type type) {
		if (type instanceof NameQualifiedType) {
			final NameQualifiedType nqt = (NameQualifiedType) type;
			resultBuilder.append(nqt.getQualifier().getFullyQualifiedName())
					.append('.')
					.append(nqt.getName().getIdentifier());
		} else if (type instanceof PrimitiveType) {
			resultBuilder.append(((PrimitiveType) type).getPrimitiveTypeCode());
		} else if (type instanceof QualifiedType) {
			final QualifiedType qualType = (QualifiedType) type;
			buildTypeString(resultBuilder, qualType.getQualifier());
			resultBuilder.append('.')
					.append(qualType.getName().getIdentifier());
		} else if (type instanceof SimpleType) {
			resultBuilder.append(((SimpleType) type).getName().getFullyQualifiedName());
		} else if (type instanceof WildcardType) {
			resultBuilder.append('?');
		} else if (type instanceof ArrayType) {
			final ArrayType arrayType = (ArrayType) type;
			buildTypeString(resultBuilder, arrayType.getElementType());
			for (int i = 0; i < arrayType.getDimensions(); ++i) {
				resultBuilder.append("[]");
			}
		} else if (type instanceof ParameterizedType) {
			final ParameterizedType paramType = (ParameterizedType) type;
			buildTypeString(resultBuilder, paramType.getType());

			resultBuilder.append('<');

			boolean first = true;
			for (final Type typeParam : (List<Type>) paramType.typeArguments()) {
				if (!first) {
					resultBuilder.append(", ");
				}
				first = false;
				buildTypeString(resultBuilder, typeParam);
			}

			resultBuilder.append('>');
		}
	}



	private static String getTypeString(final Type type, final int dimensions,
			final boolean isVarargs) {

		final StringBuilder resultBuilder = new StringBuilder();
		buildTypeString(resultBuilder, type);

		if (isVarargs) {
			resultBuilder.append("[]");
		}

		for (int i = 0; i < dimensions; ++i) {
			resultBuilder.append("[]");
		}

		return resultBuilder.toString();
	}



	private static String getMethodName(final MethodDeclaration decl) {
		final StringBuilder nameBuilder = new StringBuilder();
		nameBuilder.append(decl.getName().getIdentifier()).append('(');

		if (!decl.parameters().isEmpty()) {
			final StringJoiner joiner = new StringJoiner(", ");
			for (final SingleVariableDeclaration param : (List<SingleVariableDeclaration>)
					decl.parameters()) {
				joiner.add(getTypeString(param.getType(), param.getExtraDimensions(), param.isVarargs()));
			}
			nameBuilder.append(joiner.toString());
		}

		nameBuilder.append(')');

		return nameBuilder.toString();
	}



	private static String removePunctuation(final String s) {
		int o = s.length();
		while (o > 0 && (s.charAt(o - 1) == '.' || s.charAt(o - 1) == ','
				|| s.charAt(o - 1) == ':' || s.charAt(o - 1) == ';'
				|| s.charAt(o - 1) == '!' || s.charAt(o - 1) == '?')) {
			o -= 1;
		}

		if (o < s.length()) {
			return s.substring(0, o);
		}
		return s;
	}



	private static void handleFragments(final StringBuilder docBuilder, final TagElement tag,
			final boolean allowTransformations) {

		for (final IDocElement elem : (List<IDocElement>) tag.fragments()) {
			if (elem instanceof MemberRef) {
				final MemberRef memberRef = (MemberRef) elem;
				if (memberRef.getQualifier() != null) {
					docBuilder.append(memberRef.getQualifier().getFullyQualifiedName());
				}
				docBuilder.append('#').append(memberRef.getName().getIdentifier()).append(' ');
			} else if (elem instanceof MethodRef) {
				final MethodRef methodRef = (MethodRef) elem;
				if (methodRef.getQualifier() != null) {
					docBuilder.append(methodRef.getQualifier().getFullyQualifiedName());
				}
				docBuilder.append('#').append(methodRef.getName().getIdentifier()).append(' ');
			} else if (elem instanceof Name) {
				docBuilder.append(((Name) elem).getFullyQualifiedName()).append(' ');
			} else if (elem instanceof TagElement) {
				final TagElement tagElem = (TagElement) elem;
				switch (tagElem.getTagName()) {
					case "@link":
					case "@linkplain":
					case "@value":
					case "@code":
					case "@literal":
						handleFragments(docBuilder, tagElem, false);
						docBuilder.append(' ');
						break;

					default:
						// Ignore
				}
			} else if (elem instanceof TextElement) {
				if (allowTransformations) {
					final String text = StringEscapeUtils.unescapeHtml4(
							((TextElement) elem).getText().replaceAll("<[^>]+/?>", " "));

					final String[] parts = text.split("\\s+");

					for (int i = 0; i < parts.length; ++i) {
						final String token = removePunctuation(parts[i]);

						if (token.isEmpty()) {
							continue;
						}

						final String convToken = DO_NOT_CONVERT_TO_LOWER.matcher(token).matches()
								? token
								: token.toLowerCase(Locale.ENGLISH);

						// Apply transformations
						final String transToken;
						switch (convToken) {
							case "can't":
								transToken = "cannot";
								break;

							case "won't":
								transToken = "will not";
								break;

							case "i'm":
								transToken = "i am";
								break;

							case "spec'ed":
								transToken = "specified";
								break;

							case "exec'ing":
								transToken = "executing";
								break;

							case "zero'd":
								transToken = "zeroed";
								break;

							case "add'ing":
								transToken = "adding";
								break;

							case "remove'ing":
								transToken = "removing";
								break;

							case "i.e.":
							case "i.e":
								transToken = "that is";
								break;

							case "e.g.":
							case "e.g":
								transToken = "for example";
								break;

							case "can":
								if (i + 1 < parts.length && "not".equals(removePunctuation(parts[i + 1]))) {
									i += 1;
									transToken = "cannot";
									break;
								}
								// fall through

							default: {
								final Matcher mNot1 = TF_NOT1.matcher(convToken);
								if (mNot1.matches()) {
									transToken = mNot1.group(1) + " not";
									break;
								}
								final Matcher mNot2 = TF_NOT2.matcher(convToken);
								if (mNot2.matches()) {
									transToken = mNot2.group(1) + " not";
									break;
								}
								final Matcher mAre = TF_ARE.matcher(convToken);
								if (mAre.matches()) {
									transToken = mAre.group(1) + " are";
									break;
								}
								final Matcher mWill = TF_WILL.matcher(convToken);
								if (mWill.matches()) {
									transToken = mWill.group(1) + " will";
									break;
								}
								final Matcher mHave = TF_HAVE.matcher(convToken);
								if (mHave.matches()) {
									transToken = mHave.group(1) + " have";
									break;
								}
								final Matcher mWould = TF_WOULD.matcher(convToken);
								if (mWould.matches()) {
									transToken = mWould.group(1) + " would";
									break;
								}
								transToken = convToken;
							}
						}

						docBuilder.append(transToken).append(' ');
					}
				} else {
					docBuilder.append(((TextElement) elem).getText()).append(' ');
				}
			}
		}
	}



	private static void handleMethodDocs(final File file,
			final String className, final String methodName,
			final List<TagElement> docTags) {

		if (filterMethod(methodName)) {
			final StringBuilder docBuilder = new StringBuilder();
			for (final TagElement tag : docTags) {
				if (tag.getTagName() != null) {
					switch (tag.getTagName()) {
						case "@param":
							docBuilder.append("parameter ");
							break;

						case "@return":
							docBuilder.append("returns ");
							break;

						// TODO

						default:
							continue;
					}
				}

				handleFragments(docBuilder, tag, true);
				docBuilder.append(' ');
			}

			storeDocs(file, className, methodName, docBuilder.toString());
		}
	}



	private static void storeDocs(final File file, final String className, final String methodName,
			final String docs) {

		if (!docs.trim().isEmpty()) {
			try {
				docStmt.setInt(1, currentId);
				docStmt.setInt(2, currentProjectId);
				docStmt.setString(3, file.toString());
				docStmt.setString(4, className + "." + methodName);
				docStmt.setString(5, docs);
				docStmt.execute();
			} catch (final SQLException e) {
				throw new RuntimeException(e);
			}

			currentId += 1;
		}
	}



	@SuppressWarnings({ "rawtypes" })
	private static void processFile(final File file) {
		try {
			final ASTParser parser = ASTParser.newParser(AST.JLS8);

			final char[] contentsArray = FileUtils
					.readFileToString(file, Charset.defaultCharset()).toCharArray();
			parser.setSource(contentsArray);

			final Map options = JavaCore.getOptions();
			JavaCore.setComplianceOptions(JavaCore.VERSION_11, options);
			parser.setCompilerOptions(options);
			try {
				final CompilationUnit root = (CompilationUnit) parser.createAST(null);

				root.accept(new MethodDocGeneratorVisitor(file));
			} catch (final IllegalArgumentException e) {
				System.out.println("Cannot parse " + file + ", ignoring");
			}
		} catch (final IOException e) {
			e.printStackTrace();
			System.exit(2);
		}
	}



	private static boolean filterMethod(final String methodName) {
		// Exclude: equals, hashCode, toString
		return !"equals(Object)".equals(methodName)
				&& !"equals(java.lang.Object)".equals(methodName)
				&& !"hashCode()".equals(methodName)
				&& !"toString()".equals(methodName);
	}



	private static boolean filterFile(final File file) {

		if (!fileFilter) {
			return true;
		}

		final boolean isTestFile = file.getName().endsWith("Test.java")
				|| file.getName().endsWith("TestCase.java")
				|| file.getName().endsWith("Tests.java")
				|| file.getName().startsWith("Test");

		File current = file.getParentFile();
		while (current != null) {
			final String curName = current.getName();
			if ("branches".equals(curName) || "tags".equals(curName)
					|| (isTestFile && ("test".equals(curName) || "tests".equals(curName)))) {
				return false;
			}
			current = current.getParentFile();
		}
		return true;
	}



	private static boolean isInTestDirectory(final File file) {
		File current = file.getParentFile();
		while (current != null) {
			final String curName = current.getName();
			if ("test".equals(curName) || "tests".equals(curName)) {
				return true;
			}
			current = current.getParentFile();
		}
		return false;
	}



	private static void walk(final File file) {
		if (file.isDirectory()) {
			for (final File child : file.listFiles()) {
				walk(child);
			}
		} else {
			final int dotIndex = file.getName().lastIndexOf('.');
			if (dotIndex >= 0
					&& ".java".equalsIgnoreCase(file.getName().substring(dotIndex))
					&& filterFile(file)) {
				processFile(file);
			}
		}
	}



	public static void main(String[] args) {
		Class jdbc = org.sqlite.JDBC.class; // Ensure class is loaded

		try (final Connection conn = DriverManager.getConnection("jdbc:sqlite:docs.db")) {
			conn.setAutoCommit(false);

			final Statement stmt = conn.createStatement();
			stmt.execute("CREATE TABLE IF NOT EXISTS projects (id INT PRIMARY KEY, name TEXT)");
			stmt.execute("CREATE TABLE IF NOT EXISTS internal_filtered_methoddocs "
					+ "(id INT PRIMARY KEY, project_id INT, file TEXT, method TEXT, kwset TEXT)");

			final ResultSet resultProjectId = stmt
					.executeQuery("SELECT coalesce(max(id), -1) FROM projects");
			if (!resultProjectId.next()) {
				throw new IllegalStateException();
			}
			currentProjectId = resultProjectId.getInt(1) + 1;

			final ResultSet resultId = stmt
					.executeQuery("SELECT coalesce(max(id), -1) FROM internal_filtered_methoddocs");
			if (!resultId.next()) {
				throw new IllegalStateException();
			}
			currentId = resultId.getInt(1) + 1;

			final PreparedStatement projStmt = conn
					.prepareStatement("INSERT INTO projects VALUES (?, ?)");

			docStmt = conn.prepareStatement("INSERT INTO internal_filtered_methoddocs "
					+ "VALUES (?, ?, ?, ?, ?)");

			for (final String projectDir : args) {
				final File projectDirFile = new File(projectDir);

				projStmt.setInt(1, currentProjectId);
				projStmt.setString(2, projectDirFile.getName());
				projStmt.execute();

				walk(projectDirFile);

				currentProjectId += 1;
			}

			conn.commit();
		} catch (final SQLException e) {
			e.printStackTrace();
			System.exit(-3);
		}
	}
}

