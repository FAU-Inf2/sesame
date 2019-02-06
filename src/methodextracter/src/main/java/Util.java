import java.io.File;
import java.io.IOException;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.StringJoiner;

import org.apache.commons.io.FileUtils;

import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.core.dom.AbstractTypeDeclaration;
import org.eclipse.jdt.core.dom.AnnotationTypeDeclaration;
import org.eclipse.jdt.core.dom.ArrayType;
import org.eclipse.jdt.core.dom.AST;
import org.eclipse.jdt.core.dom.ASTNode;
import org.eclipse.jdt.core.dom.ASTParser;
import org.eclipse.jdt.core.dom.ASTVisitor;
import org.eclipse.jdt.core.dom.BodyDeclaration;
import org.eclipse.jdt.core.dom.CompilationUnit;
import org.eclipse.jdt.core.dom.EnumDeclaration;
import org.eclipse.jdt.core.dom.MethodDeclaration;
import org.eclipse.jdt.core.dom.NameQualifiedType;
import org.eclipse.jdt.core.dom.ParameterizedType;
import org.eclipse.jdt.core.dom.PrimitiveType;
import org.eclipse.jdt.core.dom.QualifiedType;
import org.eclipse.jdt.core.dom.SimpleType;
import org.eclipse.jdt.core.dom.SingleVariableDeclaration;
import org.eclipse.jdt.core.dom.Type;
import org.eclipse.jdt.core.dom.TypeDeclaration;
import org.eclipse.jdt.core.dom.WildcardType;

public class Util {

	public static MethodDeclaration matchFunction(final String funcSpec,
			final List<AbstractTypeDeclaration> types) {

		String funcName = funcSpec;
		ArrayList<String> classSpec = null;
		ArrayList<String> paramSpec = null;

		// Parameters
		final int parenOpenIndex = funcSpec.indexOf('(');
		if (parenOpenIndex != -1) {
			final int parenCloseIndex = funcSpec.lastIndexOf(')');
			if (parenCloseIndex <= parenOpenIndex) {
				throw new IllegalArgumentException();
			}

			final String paramStr = funcName.substring(parenOpenIndex + 1, parenCloseIndex).trim();
			funcName = funcName.substring(0, parenOpenIndex);

			if (paramStr.isEmpty()) {
				paramSpec = new ArrayList<>(0);
			} else {
				paramSpec = new ArrayList<>();
				int start = 0;
				int level = 0;
				for (int i = 0; i < paramStr.length(); ++i) {
					switch (paramStr.charAt(i)) {
						case '<':
							level += 1;
							break;
						case '>':
							level -= 1;
							break;
						case ',':
							if (level == 0) {
								paramSpec.add(paramStr.substring(start, i).trim());
								start = i + 1;
							}
							break;
						default:
							break;
					}
				}
				paramSpec.add(paramStr.substring(start).trim());
			}
		}

		// Class names
		if (funcName.contains(".")) {
			final String[] nameParts = funcName.split("\\.");
			funcName = nameParts[nameParts.length - 1];
			classSpec = new ArrayList<>(nameParts.length - 1);
			for (int i = 0; i < nameParts.length - 1; ++i) {
				classSpec.add(nameParts[i]);
			}
		}

		for (final AbstractTypeDeclaration decl : types) {
			final MethodDeclaration match = lookupMatch(decl, funcName, classSpec, 0, paramSpec);
			if (match != null) {
				return match;
			}
		}
		return null;
	}



	private static MethodDeclaration lookupMatch(final BodyDeclaration decl,
			final String funcName, final ArrayList<String> classSpec, final int classSpecIndex,
			final ArrayList<String> paramSpec) {

		if (decl instanceof AbstractTypeDeclaration) {
			final AbstractTypeDeclaration typeDecl = (AbstractTypeDeclaration) decl;
			// Enter class, if class name matches or class is a first class object
			// and no class names are specified
			if (((classSpec != null) && (classSpecIndex < classSpec.size())
						&& typeDecl.getName().getIdentifier().equals(classSpec.get(classSpecIndex)))
					|| ((classSpec == null) && (classSpecIndex == 0))) {

				for (final BodyDeclaration innerDecl
						: (List<BodyDeclaration>) typeDecl.bodyDeclarations()) {

					final MethodDeclaration match
							= lookupMatch(innerDecl, funcName, classSpec, classSpecIndex + 1, paramSpec);
					if (match != null) {
						return match;
					}
				}
			}
		} else if (decl instanceof MethodDeclaration) {
			final MethodDeclaration methodDecl = (MethodDeclaration) decl;
			if (((classSpec == null) || (classSpecIndex == classSpec.size()))
					&& methodDecl.getName().getIdentifier().equals(funcName)) {

				if (paramSpec != null) {
					final List<SingleVariableDeclaration> params
							= (List<SingleVariableDeclaration>) methodDecl.parameters();

					if (paramSpec.size() != params.size()) {
						return null;
					}


					int counter = 0;
					for (final SingleVariableDeclaration param : params) {
						if (!paramSpec.get(counter).equals(getTypeString(param.getType(),
									param.getExtraDimensions(), param.isVarargs(), false)) &&
								!paramSpec.get(counter).equals(getTypeString(param.getType(),
									param.getExtraDimensions(), param.isVarargs(), true))) {
							return null;
						}

						counter += 1;
					}
				}

				return methodDecl;
			}
		}
		return null;
	}



	private static String getTypeString(final Type type, final int dimensions,
			final boolean isVarargs, final boolean typeErasure) {

		final StringBuilder resultBuilder = new StringBuilder();
		resultBuilder.append(getTypeString(type, isVarargs, typeErasure));

		for (int i = 0; i < dimensions; ++i) {
			resultBuilder.append("[]");
		}

		return resultBuilder.toString();
	}



	private static String getTypeString(final Type type, final boolean isVarargs,
			final boolean typeErasure) {

		String result = null;
		if (type instanceof NameQualifiedType) {
			final NameQualifiedType nqt = (NameQualifiedType) type;
			result = nqt.getQualifier().getFullyQualifiedName() + "." + nqt.getName().getIdentifier();
		} else if (type instanceof PrimitiveType) {
			result = ((PrimitiveType) type).getPrimitiveTypeCode().toString();
		} else if (type instanceof QualifiedType) {
			final QualifiedType qualType = (QualifiedType) type;
			result = getTypeString(qualType.getQualifier(), false, typeErasure) + "."
					+ qualType.getName().getIdentifier();
		} else if (type instanceof SimpleType) {
			result = ((SimpleType) type).getName().getFullyQualifiedName();
		} else if (type instanceof WildcardType) {
			result = "?";
		} else if (type instanceof ArrayType) {
			final ArrayType arrayType = (ArrayType) type;
			result = getTypeString(arrayType.getElementType(), false, typeErasure);
			for (int i = 0; i < arrayType.getDimensions(); ++i) {
				result += "[]";
			}
		} else if (type instanceof ParameterizedType) {
			final ParameterizedType paramType = (ParameterizedType) type;
			result = getTypeString(paramType.getType(), false, typeErasure);
			if (!typeErasure) {
				final StringJoiner paramJoiner = new StringJoiner(", ", "<", ">");
				for (final Type typeParam : (List<Type>) paramType.typeArguments()) {
					paramJoiner.add(getTypeString(typeParam, false, false));
				}
				result += paramJoiner.toString();
			}
		}

		if (result != null && isVarargs) {
			result += "[]";
		}
		return result;
	}



	public static void printMatching(final CompilationUnit root, final String methodName) {
		root.accept(new ASTVisitor() {
			@Override
			public void endVisit(final MethodDeclaration node) {
				if (node.getName().getIdentifier().equals(methodName)) {
					final List<SingleVariableDeclaration> params
							= (List<SingleVariableDeclaration>) node.parameters();

					final StringJoiner paramJoiner = new StringJoiner(", ", "(", ")");
					for (final SingleVariableDeclaration param : params) {
						paramJoiner.add(getTypeString(param.getType(), param.getExtraDimensions(),
								param.isVarargs(), false));
					}

					System.out.println(methodName + paramJoiner.toString());
				}
				super.endVisit(node);
			}
		});
	}
}

