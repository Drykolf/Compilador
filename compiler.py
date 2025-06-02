from source.parser import Parser
from source.checker import Checker
from source.lexer import Lexer
from source.ircode import IRCode
from source.stack_machine import StackMachine
from rich import print
import json,os

# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'settings', 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: config.json not found, using default settings")
        return {"Debug": False, "GenerateOutputFile": False}
    except json.JSONDecodeError:
        print("Warning: Invalid JSON in config.json, using default settings")
        return {"Debug": False, "GenerateOutputFile": False}

CONFIG = load_config()# Global configuration

def read_file(file_path):
    """Read the content of a file and return it as a string."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def create_output_directory(filePath):
    """Create an output directory based on the file name."""
    fileName = filePath.split('/')[-1].split('\\')[-1].split('.')[0]
    if CONFIG.get("GenerateOutputFile", False):
        output_dir = os.path.join(os.path.dirname(__file__), 'output', fileName)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    return fileName

def compile(file):
    debug = CONFIG.get("Debug", False)
    content = read_file(file)# Leer el archivo de entrada
    fileName = create_output_directory(file)  # Crear el directorio de salida si es necesario
    #try:
    lex = Lexer(fileName)# Crear el analizador lexico
    fileTokens = lex.tokenize(content)
    if debug: print(fileTokens)  # Imprimir los tokens si el modo debug está activado
    parser = Parser(fileTokens,fileName)
    top = parser.parse()  # Devuelve directamente el AST como un Program -> lista de statements
    statements = top.stmts  # Convertir a lista de statements
    if debug: print(statements)  # Imprimir el AST si el modo debug está activado
    systab = Checker.check(top,fileName)  # Perform semantic checks
    if debug:systab.print()  # Print the symbol table
    module = IRCode.gencode(statements, fileName)
    if debug:module.dump()
    vm = StackMachine()
    vm.load_module(module)  # Cargar el módulo IR en la máquina virtual
    vm.run()  # Ejecutar el código IR
   # except Exception as e:
    #    print(f"{e}")
    
def debug():
    # Debugging function to check the output of the main function
    print("[bold yellow][DEBUG][/bold yellow] Debugging...")
    file = 'tests/prueba12.gox'
    compile(file)

def main():
    import sys
    if len(sys.argv) != 2:
        print('Uso: python3 check.py <archivo>')
        sys.exit(1)
    file = sys.argv[1]
    compile(file)

if __name__ == '__main__':
	#main()
	debug()

'''
problemas en prueba 9
'''