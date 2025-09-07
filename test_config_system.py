#!/usr/bin/env python3
"""
Test script for the new configuration and database system
Tests both SQLite and Oracle configurations (if available)
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add the modules directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src" / "python" / "modules"))

def test_configuration_loading():
    """Test configuration loading from YAML and JSON"""
    print("🧪 Testing Configuration Loading...")
    
    try:
        from config_loader import get_config, reload_config, get_environment
        
        # Test default environment
        os.environ['ENVIRONMENT'] = 'development'
        config = get_config()
        
        print(f"✅ Loaded config for environment: {get_environment()}")
        print(f"✅ Database type: {config.get('database', {}).get('type', 'unknown')}")
        print(f"✅ Kubernetes namespace: {config.get('kubernetes', {}).get('namespace', 'unknown')}")
        
        # Test reload functionality
        config2 = reload_config('staging')
        print(f"✅ Reloaded config for staging environment")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

def test_database_initialization():
    """Test database initialization with different configurations"""
    print("\n🧪 Testing Database Initialization...")
    
    try:
        from database import HistoryManager, get_database_config
        
        # Test SQLite configuration
        sqlite_config = {
            'type': 'sqlite',
            'path': 'test_database.db',
            'max_connections': 3
        }
        
        print("✅ Testing SQLite database...")
        history_manager = HistoryManager(sqlite_config)
        stats = history_manager.get_database_stats()
        print(f"✅ SQLite stats: {stats.get('total_records', 0)} records")
        history_manager.close()
        
        # Clean up test database
        if os.path.exists('test_database.db'):
            os.remove('test_database.db')
        
        print("✅ SQLite test completed")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def test_oracle_availability():
    """Test Oracle database availability"""
    print("\n🧪 Testing Oracle Database Availability...")
    
    try:
        import oracledb
        print("✅ oracledb module is available")
        print(f"✅ oracledb version: {oracledb.version}")
        
        from oracle_adapter import OracleAdapter, ORACLE_AVAILABLE
        if ORACLE_AVAILABLE:
            print("✅ Oracle adapter is available")
        else:
            print("❌ Oracle adapter reports not available")
        
        return True
        
    except ImportError as e:
        print(f"⚠️  Oracle not available: {e}")
        print("💡 Install with: pip install oracledb")
        return False
    except Exception as e:
        print(f"❌ Oracle test failed: {e}")
        return False

def test_environment_setup():
    """Test environment-specific settings"""
    print("\n🧪 Testing Environment-Specific Settings...")
    
    environments = ['development', 'staging', 'production']
    results = {}
    
    for env in environments:
        try:
            os.environ['ENVIRONMENT'] = env
            from config_loader import reload_config
            config = reload_config(env)
            
            db_type = config.get('database', {}).get('type', 'unknown')
            retention = config.get('data_retention', {}).get('history_days', 0)
            log_level = config.get('logging', {}).get('level', 'unknown')
            
            results[env] = {
                'db_type': db_type,
                'retention_days': retention,
                'log_level': log_level,
                'success': True
            }
            
            print(f"✅ {env.upper()}: DB={db_type}, Retention={retention}d, Log={log_level}")
            
        except Exception as e:
            results[env] = {'success': False, 'error': str(e)}
            print(f"❌ {env.upper()}: Failed - {e}")
    
    return all(r.get('success', False) for r in results.values())

def test_yaml_support():
    """Test YAML configuration support"""
    print("\n🧪 Testing YAML Support...")
    
    try:
        import yaml
        print("✅ PyYAML is available")
        
        # Test YAML parsing
        yaml_content = """
        test:
          database:
            type: sqlite
            path: test.db
          application:
            title: Test App
        """
        
        parsed = yaml.safe_load(yaml_content)
        assert parsed['test']['database']['type'] == 'sqlite'
        print("✅ YAML parsing works correctly")
        
        return True
        
    except ImportError:
        print("❌ PyYAML not available - Configuration system requires YAML")
        print("💡 Install with: pip install PyYAML")
        return False
    except Exception as e:
        print(f"❌ YAML test failed: {e}")
        return False

def create_test_summary(results):
    """Create a summary of test results"""
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print("-" * 60)
    print(f"Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The system is ready to use.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

def main():
    """Run all configuration and database tests"""
    print("🚀 Spark Pod Resource Monitor - Configuration & Database Tests")
    print("=" * 70)
    
    # Store original environment
    original_env = os.environ.get('ENVIRONMENT')
    
    try:
        # Run all tests
        results = {
            'Configuration Loading': test_configuration_loading(),
            'Database Initialization': test_database_initialization(),
            'Oracle Availability': test_oracle_availability(),
            'Environment Setup': test_environment_setup(),
            'YAML Support': test_yaml_support()
        }
        
        # Create summary
        all_passed = create_test_summary(results)
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if not results.get('Oracle Availability', False):
            print("• Install Oracle driver: pip install oracledb")
        if not results.get('YAML Support', False):
            print("• Install YAML support: pip install PyYAML")
        
        print("\n📚 For detailed configuration help, see: config/README.md")
        
        return 0 if all_passed else 1
        
    finally:
        # Restore original environment
        if original_env:
            os.environ['ENVIRONMENT'] = original_env
        elif 'ENVIRONMENT' in os.environ:
            del os.environ['ENVIRONMENT']

if __name__ == '__main__':
    sys.exit(main())
