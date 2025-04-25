from source.parser import Parser
from source.checker import Checker
from source.lexer import Lexer
from rich import print

DEBUG = True
def read_file(file_path):
    """Read the content of a file and return it as a string."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def main():
    import sys
    if len(sys.argv) != 2:
        print('Uso: python3 check.py <archivo>')
        sys.exit(1)
    file = sys.argv[1]
    compile(file)

def compile(file):
    content = read_file(file)# Leer el archivo de entrada
    try:
        lex = Lexer(DEBUG)# Crear el analizador lexico
        fileTokens = lex.tokenize(content)
        parser = Parser(fileTokens, DEBUG)
        ast_data = parser.parse()  # Devuelve directamente el AST como un Program -> lista de statements
        checker = Checker()  # Crear el verificador semántico
        systab = checker.check(ast_data)  # Perform semantic checks
    except Exception as e:
        return
    systab.print()  # Print the symbol table

def debug():
    # Debugging function to check the output of the main function
    print("Debugging...")
    file = 'tests/test.gox'
    compile(file)

if __name__ == '__main__':
	#main()
	debug()