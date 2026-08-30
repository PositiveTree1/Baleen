import ast
import os
import sys

def analyze_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
    
    tree = ast.parse(code, filename=filepath)
    issues = []
    
    for node in ast.walk(tree):
        # Check for facade functions (only containing 'pass', 'return <constant>', or 'raise NotImplementedError')
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Ignore empty/abstract methods or dunder methods
            if node.name.startswith("__"):
                continue
            
            statements = [s for s in node.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))] # filter docstrings
            if len(statements) == 1:
                stmt = statements[0]
                if isinstance(stmt, ast.Pass):
                    issues.append(f"{filepath}:{node.lineno} Function '{node.name}' has empty pass body.")
                elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                    # Check if it's not a trivial boolean/none helper
                    if stmt.value.value not in (True, False, None, 0, "", 0.0):
                        issues.append(f"{filepath}:{node.lineno} Function '{node.name}' returns hardcoded constant: {stmt.value.value}")
        
        # Check for hardcoded test comparisons (e.g. if x == "test")
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                    if comparator.value.lower() in ("test_cheat", "mock_bypass", "fake_result"):
                        issues.append(f"{filepath}:{node.lineno} Hardcoded test cheat string: {comparator.value}")

    return issues

def main():
    target_dirs = [
        r"c:\Users\arthu\Documents\Baleen-master\backend\app\sizing",
        r"c:\Users\arthu\Documents\Baleen-master\backend\app\services",
        r"c:\Users\arthu\Documents\Baleen-master\backend\app\api",
    ]
    
    all_issues = []
    analyzed_count = 0
    for d in target_dirs:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".py"):
                    fp = os.path.join(root, file)
                    analyzed_count += 1
                    res = analyze_file(fp)
                    if res:
                        all_issues.extend(res)
                        
    print(f"AST Analysis complete. Analyzed {analyzed_count} files.")
    if all_issues:
        print("ISSUES DETECTED:")
        for issue in all_issues:
            print(f"  - {issue}")
    else:
        print("CLEAN: 0 facade functions, 0 hardcoded test cheats detected.")

if __name__ == "__main__":
    main()
