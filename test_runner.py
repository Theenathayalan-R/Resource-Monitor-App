#!/usr/bin/env python3
"""
Test runner script for Spark Pod Resource Monitor
Runs all tests with proper setup and reporting
"""
import os
import sys
import subprocess
import logging
import time
from pathlib import Path

# Add the source directory to Python path
src_dir = Path(__file__).parent / 'src' / 'python'
modules_dir = src_dir / 'modules'
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(modules_dir))

# Import logging setup
try:
    from modules.logging_config import setup_logging
except Exception:
    # Fallback logging setup
    def setup_logging(level='INFO', log_file=None):
        logging.basicConfig(level=getattr(logging, level))


def run_pytest_tests():
    """Run all tests using pytest"""
    print("🧪 Running All Tests with pytest...")
    print("=" * 60)
    
    # Change to the src/python directory where tests are located
    original_dir = os.getcwd()
    os.chdir(src_dir)
    
    try:
        # Set environment variables for proper module resolution
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{modules_dir}:{src_dir}"
        
        # Run pytest with verbose output and coverage if available
        cmd = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '-v',
            '--tb=short',
            '--no-header',
            '--color=yes'
        ]
        
        # Add coverage if pytest-cov is available
        try:
            import pytest_cov
            cmd.extend(['--cov=modules', '--cov-report=term-missing'])
        except ImportError:
            pass
        
        print(f"Running command: {' '.join(cmd)}")
        print(f"Working directory: {os.getcwd()}")
        print(f"PYTHONPATH: {env.get('PYTHONPATH', 'Not set')}")
        print()
        
        # Run the tests
        result = subprocess.run(cmd, env=env, capture_output=False, text=True)
        
        return result.returncode == 0, result.returncode
        
    except Exception as e:
        print(f"❌ Failed to run tests: {str(e)}")
        return False, 1
    finally:
        os.chdir(original_dir)

def run_specific_test_category(category=""):
    """Run specific category of tests"""
    if not category:
        return run_pytest_tests()
    
    print(f"🧪 Running {category} Tests...")
    print("=" * 60)
    
    original_dir = os.getcwd()
    os.chdir(modules_dir)
    
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(modules_dir)
        
        # Run specific test patterns
        if category == "integration":
            pattern = "tests/test_integration.py"
        elif category == "unit":
            pattern = "tests/test_*.py -k 'not test_integration'"
        elif category == "performance":
            pattern = "tests/test_integration.py::TestPerformanceBenchmarks"
        else:
            pattern = "tests/"
        
        cmd = [
            sys.executable, '-m', 'pytest',
            pattern,
            '-v',
            '--tb=short',
            '--no-header'
        ]
        
        result = subprocess.run(cmd, env=env)
        return result.returncode == 0, result.returncode
        
    except Exception as e:
        print(f"❌ Failed to run {category} tests: {str(e)}")
        return False, 1
    finally:
        os.chdir(original_dir)


def check_dependencies():
    """Check if all required dependencies are installed"""
    print("📦 Checking Dependencies...")
    print("=" * 60)
    
    required_modules = [
        'streamlit', 'pandas', 'sqlite3', 'kubernetes', 
        'psutil', 'tenacity', 'pytest'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - MISSING")
            missing.append(module)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    return True


def check_code_quality():
    """Check code quality with basic linting"""
    print("\n📝 Code Quality Checks...")
    print("=" * 60)
    
    issues = 0
    
    # Check for basic Python syntax issues
    python_files = list(src_dir.rglob('*.py'))
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                compile(content, py_file, 'exec')
            print(f"✅ {py_file.relative_to(src_dir)}")
        except SyntaxError as e:
            print(f"❌ Syntax error in {py_file.relative_to(src_dir)}: {str(e)}")
            issues += 1
        except Exception as e:
            print(f"⚠️ Warning for {py_file.relative_to(src_dir)}: {str(e)}")
    
    return issues == 0


def generate_test_report(success, return_code, total_time):
    """Generate a comprehensive test report"""
    print("\n" + "=" * 80)
    print("📊 TEST REPORT SUMMARY")
    print("=" * 80)
    
    # Overall status
    status_icon = "✅" if success else "❌"
    status_text = "PASSED" if success else "FAILED"
    
    print(f"{status_icon} Overall Status: {status_text}")
    print(f"⏱️ Total Runtime: {total_time:.2f} seconds")
    print(f"🔧 Return Code: {return_code}")
    print()
    
    # Recommendations
    print("Recommendations:")
    if success:
        print("  • All tests passed! ✅")
        print("  • Ready for production deployment 🚀")
        print("  • Consider monitoring performance metrics in production")
        print("  • Keep adding more edge case tests for robustness")
    else:
        print("  • ❌ Some tests failed - review the output above")
        print("  • Fix failing tests before deployment")
        print("  • Check logs for detailed error information")
        print("  • Ensure all dependencies are installed correctly")
    
    print("\nNext Steps:")
    if success:
        print("  1. Deploy to staging environment")
        print("  2. Run integration tests in staging")
        print("  3. Monitor performance metrics")
        print("  4. Deploy to production")
    else:
        print("  1. Review test failures above")
        print("  2. Fix identified issues")
        print("  3. Re-run tests")
        print("  4. Repeat until all tests pass")
    
    return success


def main():
    """Main test runner"""
    print("🚀 Spark Pod Resource Monitor - Test Suite")
    print("=" * 80)
    
    # Setup logging for tests
    try:
        setup_logging('INFO', 'logs/test_run.log')
    except:
        logging.basicConfig(level=logging.INFO)
    
    start_time = time.time()
    
    try:
        # Check dependencies first
        if not check_dependencies():
            print("❌ Missing dependencies. Please install them first.")
            sys.exit(1)
        
        # Run all tests
        print("\n🎯 Running Complete Test Suite...")
        success, return_code = run_pytest_tests()
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Generate report
        final_success = generate_test_report(success, return_code, total_time)
        
        # Exit with appropriate code
        sys.exit(0 if final_success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test runner failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
