import java.io.File;
import java.io.IOException;
import java.nio.charset.Charset;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Set;
import java.util.StringJoiner;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.commons.io.FileUtils;

import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.core.ToolFactory;
import org.eclipse.jdt.core.dom.AbstractTypeDeclaration;
import org.eclipse.jdt.core.dom.AnnotationTypeDeclaration;
import org.eclipse.jdt.core.dom.ArrayType;
import org.eclipse.jdt.core.dom.AST;
import org.eclipse.jdt.core.dom.ASTNode;
import org.eclipse.jdt.core.dom.ASTParser;
import org.eclipse.jdt.core.dom.ASTVisitor;
import org.eclipse.jdt.core.dom.BodyDeclaration;
import org.eclipse.jdt.core.dom.ClassInstanceCreation;
import org.eclipse.jdt.core.dom.CompilationUnit;
import org.eclipse.jdt.core.dom.ConstructorInvocation;
import org.eclipse.jdt.core.dom.CreationReference;
import org.eclipse.jdt.core.dom.EnumDeclaration;
import org.eclipse.jdt.core.dom.ExpressionMethodReference;
import org.eclipse.jdt.core.dom.FieldAccess;
import org.eclipse.jdt.core.dom.FieldDeclaration;
import org.eclipse.jdt.core.dom.IBinding;
import org.eclipse.jdt.core.dom.IMethodBinding;
import org.eclipse.jdt.core.dom.ImportDeclaration;
import org.eclipse.jdt.core.dom.ITypeBinding;
import org.eclipse.jdt.core.dom.IVariableBinding;
import org.eclipse.jdt.core.dom.MethodDeclaration;
import org.eclipse.jdt.core.dom.MethodInvocation;
import org.eclipse.jdt.core.dom.Modifier;
import org.eclipse.jdt.core.dom.NameQualifiedType;
import org.eclipse.jdt.core.dom.ParameterizedType;
import org.eclipse.jdt.core.dom.PrimitiveType;
import org.eclipse.jdt.core.dom.QualifiedName;
import org.eclipse.jdt.core.dom.QualifiedType;
import org.eclipse.jdt.core.dom.SimpleName;
import org.eclipse.jdt.core.dom.SimpleType;
import org.eclipse.jdt.core.dom.SingleVariableDeclaration;
import org.eclipse.jdt.core.dom.SuperConstructorInvocation;
import org.eclipse.jdt.core.dom.SuperFieldAccess;
import org.eclipse.jdt.core.dom.SuperMethodInvocation;
import org.eclipse.jdt.core.dom.SuperMethodReference;
import org.eclipse.jdt.core.dom.Type;
import org.eclipse.jdt.core.dom.TypeDeclaration;
import org.eclipse.jdt.core.dom.VariableDeclaration;
import org.eclipse.jdt.core.dom.WildcardType;
import org.eclipse.jdt.core.formatter.CodeFormatter;
import org.eclipse.jdt.core.formatter.DefaultCodeFormatterConstants;
import org.eclipse.jface.text.Document;
import org.eclipse.jface.text.IDocument;
import org.eclipse.text.edits.TextEdit;

public class MethodExtracter {

	private static String outputString = "";



	public static void main(String[] args) {
		try {
			final String sourceFileName = new File(args[0]).getAbsolutePath();

			final ASTParser parser = ASTParser.newParser(AST.JLS10);

			String longestPrefix = "";
			final String[] sourcepathEntries = args[2].split(":");
			for (int i = 0; i < sourcepathEntries.length; ++i) {
				sourcepathEntries[i] = new File(sourcepathEntries[i]).getAbsolutePath();
				if (sourceFileName.startsWith(sourcepathEntries[i])
						&& sourcepathEntries[i].length() > longestPrefix.length()) {
					longestPrefix = sourcepathEntries[i];
				}
			}

			parser.setEnvironment(new String[0], sourcepathEntries, null, true);
			parser.setResolveBindings(true);
			parser.setBindingsRecovery(true);

			final char[] contentsArray = FileUtils
					.readFileToString(new File(sourceFileName), Charset.defaultCharset()).toCharArray();
			parser.setSource(contentsArray);
			parser.setKind(ASTParser.K_COMPILATION_UNIT);
			parser.setUnitName(new File(longestPrefix).toPath()
					.relativize(new File(sourceFileName).toPath()).toString());

			final Map options = JavaCore.getOptions();
			JavaCore.setComplianceOptions(JavaCore.VERSION_11, options);
			parser.setCompilerOptions(options);

			final CompilationUnit root = (CompilationUnit) parser.createAST(null);

			final MethodDeclaration method = Util.matchFunction(args[1],
					(List<AbstractTypeDeclaration>) root.types());
			if (method == null) {
				System.out.println("Method " + args[1] + " not found!");
				System.exit(1);
			}

			final ITypeBinding objectBinding = root.getAST().resolveWellKnownType("java.lang.Object");

			// Print class and method structure
			final Set<String> unresolvedBindings = new HashSet<>();
			final Set<MethodDeclaration> methodSet = getMethodSet(root, method, unresolvedBindings);
			final Set<VariableDeclaration> fieldSet = getFieldSet(root, methodSet, unresolvedBindings);

			for (final ImportDeclaration impDecl : (List<ImportDeclaration>) root.imports()) {
				if (unresolvedBindings.contains(impDecl.resolveBinding().getKey())) {
					printDeclaration(contentsArray, impDecl, false);
				}
			}

			if (!outputString.isEmpty()) {
				outputString += "\n";
			}

			final List<MethodDeclaration> methods = new ArrayList<>(methodSet);
			while (!methods.isEmpty()) {
				final MethodDeclaration decl = methods.remove(0);
				final ArrayDeque<ITypeBinding> declaringClasses = new ArrayDeque<>();

				ITypeBinding current = decl.resolveBinding().getDeclaringClass();
				do {
					declaringClasses.addFirst(current);
					current = current.getDeclaringClass();
				} while (current != null);

				int i = 1;
				for (final ITypeBinding declaringClass : declaringClasses) {
					outputString += buildClassName(declaringClass, root);
					printIndent(i++);
				}
				printDeclaration(contentsArray, decl, true);

				current = declaringClasses.pollLast();
				do {
					printFields(contentsArray, current, fieldSet, 1);

					processMembers(contentsArray, methods, fieldSet, current, 1, root);

					outputString += "}\n\n";

					current = declaringClasses.pollLast();
				} while (current != null);
			}

			// Format code
			final Map formatterSettings = DefaultCodeFormatterConstants.getJavaConventionsSettings();
			formatterSettings.put(DefaultCodeFormatterConstants.FORMATTER_TAB_CHAR, DefaultCodeFormatterConstants.MIXED);
			formatterSettings.put(JavaCore.COMPILER_COMPLIANCE, JavaCore.VERSION_1_8);
			formatterSettings.put(JavaCore.COMPILER_CODEGEN_TARGET_PLATFORM, JavaCore.VERSION_1_8);
			formatterSettings.put(JavaCore.COMPILER_SOURCE, JavaCore.VERSION_1_8);
			final CodeFormatter formatter = ToolFactory.createCodeFormatter(formatterSettings);
			final TextEdit textEdit = formatter.format(CodeFormatter.K_COMPILATION_UNIT,
					outputString, 0, outputString.length(), 0, null);

			final IDocument resultDoc = new Document(outputString);
			try {
				textEdit.apply(resultDoc);
				System.out.println(resultDoc.get().replace("<", "&lt;").replace(">", "&gt;"));
			} catch (final Exception e) {
				e.printStackTrace();
				System.exit(4);
			}
		} catch (final IllegalArgumentException e) {
			if (!"Cannot execute interface method".equals(e.getMessage())) {
				e.printStackTrace();
				System.exit(3);
			}
		} catch (final IOException e) {
			e.printStackTrace();
			System.exit(2);
		}
	}



	private static Set<MethodDeclaration> getMethodSet(final CompilationUnit root,
			final MethodDeclaration start, final Set<String> unresolvedBindings) {

		if (start == null) {
			throw new IllegalArgumentException();
		}

		final Set<MethodDeclaration> resultSet = new LinkedHashSet<>();
		final Queue<MethodDeclaration> methodQueue = new ArrayDeque<>();

		resultSet.add(start);
		methodQueue.offer(start);

		while (!methodQueue.isEmpty()) {
			methodQueue.poll().accept(new ASTVisitor() {
				@Override
				public void endVisit(final CreationReference node) {
					handleBinding(node.resolveMethodBinding());
				}

				@Override
				public void endVisit(final MethodInvocation node) {
					handleBinding(node.resolveMethodBinding());
				}

				@Override
				public void endVisit(final ExpressionMethodReference node) {
					handleBinding(node.resolveMethodBinding());
				}

				@Override
				public void endVisit(final ClassInstanceCreation node) {
					handleBinding(node.resolveConstructorBinding());
				}

				@Override
				public void endVisit(final ConstructorInvocation node) {
					handleBinding(node.resolveConstructorBinding());
				}

				@Override
				public void endVisit(final SuperConstructorInvocation node) {
					handleBinding(node.resolveConstructorBinding());
				}

				@Override
				public void endVisit(final SuperMethodInvocation node) {
					handleBinding(node.resolveMethodBinding());
				}

				@Override
				public void endVisit(final SuperMethodReference node) {
					handleBinding(node.resolveMethodBinding());
				}

				private void handleBinding(final IMethodBinding binding) {
					if (binding != null) {
						final ASTNode declarationNode = root.findDeclaringNode(binding);
						if (declarationNode instanceof MethodDeclaration) {
							final MethodDeclaration methodDeclarationNode = (MethodDeclaration) declarationNode;
							if (resultSet.add(methodDeclarationNode)) {
								methodQueue.offer(methodDeclarationNode);
							}
						} else if (declarationNode == null) {
							unresolvedBindings.add(binding.getKey());
							ITypeBinding declaringClass = binding.getDeclaringClass();
							while (declaringClass != null) {
								unresolvedBindings.add(declaringClass.getKey());
								unresolvedBindings.add(declaringClass.getErasure().getKey());

								if (declaringClass.getPackage() != null) {
									unresolvedBindings.add(declaringClass.getPackage().getKey());
								}

								declaringClass = declaringClass.getDeclaringClass();
							}
						}
					}
				}
			});
		}

		return resultSet;
	}



	private static Set<VariableDeclaration> getFieldSet(final CompilationUnit root,
			final Set<MethodDeclaration> methodDeclarations, final Set<String> unresolvedBindings) {

		final Set<VariableDeclaration> resultSet = new LinkedHashSet<>();

		for (final MethodDeclaration decl : methodDeclarations) {
			decl.accept(new ASTVisitor() {
				@Override
				public void endVisit(final FieldAccess node) {
					handleBinding(node.resolveFieldBinding());
				}

				@Override
				public void endVisit(final QualifiedName node) {
					handleBinding(node.resolveBinding());
				}

				@Override
				public void endVisit(final SimpleName node) {
					handleBinding(node.resolveBinding());
				}

				@Override
				public void endVisit(final SuperFieldAccess node) {
					handleBinding(node.resolveFieldBinding());
				}

				private void handleBinding(final IBinding binding) {
					if (binding instanceof IVariableBinding) {
						handleBinding((IVariableBinding) binding);
					}
				}

				private void handleBinding(final IVariableBinding binding) {
					if (binding != null && binding.getDeclaringClass() != null) {
						final ASTNode declaringNode = root.findDeclaringNode(binding);
						if (declaringNode instanceof VariableDeclaration) {
							resultSet.add((VariableDeclaration) declaringNode);
						} else if (declaringNode == null) {
							unresolvedBindings.add(binding.getKey());

							ITypeBinding declaringClass = binding.getDeclaringClass();
							while (declaringClass != null) {
								unresolvedBindings.add(declaringClass.getKey());
								unresolvedBindings.add(declaringClass.getErasure().getKey());

								if (declaringClass.getPackage() != null) {
									unresolvedBindings.add(declaringClass.getPackage().getKey());
								}

								declaringClass = declaringClass.getDeclaringClass();
							}
						}
					}
				}
			});
		}

		return resultSet;
	}



	private static void printDeclaration(final char[] contentsArray, final ASTNode decl,
			final boolean doubleNewLine) {
		outputString += String.valueOf(Arrays.copyOfRange(contentsArray,
				decl.getStartPosition(), decl.getStartPosition() + decl.getLength()))
				+ (doubleNewLine ? "\n\n" : "\n");
	}



	private static void printFields(final char[] contentsArray, final ITypeBinding declaringClass,
			final Set<VariableDeclaration> fieldSet, final int indent) {
		
		boolean fieldsPrinted = false;
		for (final VariableDeclaration varDecl : fieldSet) {
			final IVariableBinding binding = varDecl.resolveBinding();
			if (binding != null && binding.getDeclaringClass() == declaringClass) {
				final ASTNode declParent = varDecl.getParent();
				if (declParent instanceof FieldDeclaration) {
					final FieldDeclaration fieldDecl = (FieldDeclaration) declParent;
					printIndent(indent);
					outputString += String.valueOf(Arrays.copyOfRange(contentsArray,
							fieldDecl.getStartPosition(), fieldDecl.getStartPosition() + fieldDecl.getLength()))
							+ '\n';
					fieldsPrinted = true;
				}
			}
		}

		if (fieldsPrinted) {
			outputString += '\n';
		}
	}



	private static void processMembers(final char[] contentsArray,
			final List<MethodDeclaration> methods, final Set<VariableDeclaration> fieldSet,
			final ITypeBinding declaringClass, final int depth, final CompilationUnit root) {
		
		// First process methods
		final Iterator<MethodDeclaration> methodsIter = methods.iterator();
		while (methodsIter.hasNext()) {
			final MethodDeclaration decl = methodsIter.next();
			if (decl.resolveBinding().getDeclaringClass() == declaringClass) {
				methodsIter.remove();

				printIndent(depth);
				printDeclaration(contentsArray, decl, true);
			}
		}

		// Check for inner classes
		boolean changed;
		do {
			changed = false;
			final Iterator<MethodDeclaration> methodsIter2 = methods.iterator();
			while (methodsIter2.hasNext()) {
				final MethodDeclaration decl = methodsIter2.next();
				final ITypeBinding declDeclaringClass = decl.resolveBinding().getDeclaringClass();
				if (declDeclaringClass.getDeclaringClass() == declaringClass) {
					methodsIter2.remove();

					// Anonymous classes should have already been processed
					if (!declDeclaringClass.isAnonymous()) {
						printIndent(depth);
						outputString += buildClassName(declDeclaringClass, root);

						printFields(contentsArray, declaringClass, fieldSet, depth + 1);

						printIndent(depth + 1);
						printDeclaration(contentsArray, decl, true);

						processMembers(contentsArray, methods, fieldSet, declDeclaringClass, depth + 1, root);
						printIndent(depth);
						outputString += "}\n\n";

						changed = true;
						break;
					}
				}
			}
		} while (changed);
	}



	private static String buildClassName(final ITypeBinding declaringClass,
			final CompilationUnit root) {

		final AST ast = root.getAST();

		final StringBuilder outputBuilder = new StringBuilder();
		if (declaringClass.isInterface()) {
			outputBuilder.append("interface ").append(declaringClass.getName());
			if (declaringClass.getTypeParameters() != null
					&& declaringClass.getTypeParameters().length > 0) {

				outputBuilder.append('<');
				boolean first = true;
				for (final ITypeBinding typeParam : declaringClass.getTypeParameters()) {
					if (!first) {
						outputBuilder.append(", ");
					}
					outputBuilder.append(typeParam.getName());
					first = false;
				}
				outputBuilder.append('>');
			}
			outputBuilder.append(" {\n");
		} else {
			final BodyDeclaration classDecl = (BodyDeclaration) root.findDeclaringNode(declaringClass);

			if ((classDecl.getModifiers() & Modifier.ABSTRACT) != 0) {
				outputBuilder.append("abstract ");
			}

			outputBuilder.append("class ").append(declaringClass.getName());
			if (declaringClass.getTypeParameters() != null
					&& declaringClass.getTypeParameters().length > 0) {

				outputBuilder.append('<');
				boolean first = true;
				for (final ITypeBinding typeParam : declaringClass.getTypeParameters()) {
					if (!first) {
						outputBuilder.append(", ");
					}
					outputBuilder.append(typeParam.getName());
					first = false;
				}
				outputBuilder.append('>');
			}
			if (declaringClass.getSuperclass() != ast.resolveWellKnownType("java.lang.Object")) {
				outputBuilder.append(" extends ").append(declaringClass.getSuperclass().getName());
			}
			if (declaringClass.getInterfaces() != null
					&& declaringClass.getInterfaces().length > 0) {

				outputBuilder.append(" implements ");

				boolean first = true;
				for (final ITypeBinding implInterface : declaringClass.getInterfaces()) {
					if (!first) {
						outputBuilder.append(", ");
					}
					outputBuilder.append(implInterface.getName());
					first = false;
				}
			}
			outputBuilder.append(" {\n");
		}
		return outputBuilder.toString();
	}



	private static void printIndent(final int depth) {
		for (int i = 0; i < depth; ++i) {
			outputString += "    ";
		}
	}
}

