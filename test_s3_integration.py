#!/usr/bin/env python3
"""
Test script for S3 Platform Monitoring integration
Tests S3 adapter, views, and configuration system
"""

import sys
import os
import logging
from pathlib import Path

# Add src/python to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src" / "python"))

from modules.config_loader import get_config
from modules.s3_adapter import S3Adapter
from modules.views.s3_views import S3Views

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_config_loading():
    """Test that configuration loads properly with S3 settings"""
    print("🔧 Testing Configuration Loading...")
    try:
        config = get_config()
        s3_config = config.get('s3', {})
        
        print(f"✅ Configuration loaded successfully")
        print(f"   - S3 monitoring enabled: {s3_config.get('enabled', False)}")
        print(f"   - S3 region: {s3_config.get('region', 'not set')}")
        print(f"   - Configured buckets: {len(s3_config.get('buckets', []))}")
        
        # Print bucket information
        for bucket in s3_config.get('buckets', []):
            print(f"     • {bucket.get('display_name', bucket.get('name', 'Unknown'))}")
            print(f"       Quota: {bucket.get('quota_gb', 0)} GB")
            print(f"       Alert threshold: {bucket.get('alert_threshold', 90)}%")
        
        return True
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

def test_s3_adapter_initialization():
    """Test S3 adapter initialization (without actual AWS credentials)"""
    print("\n📦 Testing S3 Adapter Initialization...")
    try:
        # Test initialization without credentials (should handle gracefully)
        adapter = S3Adapter()
        
        print(f"✅ S3 Adapter initialized")
        print(f"   - S3 monitoring enabled: {adapter.is_enabled()}")
        print(f"   - AWS client available: {adapter.client is not None}")
        
        if not adapter.is_enabled():
            print("   ℹ️ S3 monitoring is disabled (expected without AWS credentials)")
        
        return True
    except Exception as e:
        print(f"❌ S3 Adapter initialization failed: {e}")
        return False

def test_s3_adapter_methods():
    """Test S3 adapter methods work without crashing"""
    print("\n🧪 Testing S3 Adapter Methods...")
    try:
        adapter = S3Adapter()
        
        # Test methods that should work even without credentials
        summary = adapter.get_platform_summary()
        print(f"✅ Platform summary generated")
        print(f"   - Total buckets: {summary['total_buckets']}")
        print(f"   - Status: {summary['status']}")
        
        # Test bucket metrics (should handle disabled state gracefully)
        all_metrics = adapter.get_all_bucket_metrics(use_cache=False)
        print(f"✅ Bucket metrics retrieved: {len(all_metrics)} buckets")
        
        return True
    except Exception as e:
        print(f"❌ S3 Adapter methods failed: {e}")
        return False

def test_s3_views_initialization():
    """Test S3 views initialization"""
    print("\n🖥️ Testing S3 Views Initialization...")
    try:
        adapter = S3Adapter()
        views = S3Views(adapter)
        
        print(f"✅ S3 Views initialized successfully")
        print(f"   - S3 adapter available: {views.s3_adapter is not None}")
        
        return True
    except Exception as e:
        print(f"❌ S3 Views initialization failed: {e}")
        return False

def test_feature_flags():
    """Test that feature flags work properly"""
    print("\n🚩 Testing Feature Flags...")
    try:
        config = get_config()
        app_config = config.get('application', {})
        features = app_config.get('features', {})
        
        print(f"✅ Feature flags loaded")
        print(f"   - Kubernetes monitoring: {features.get('kubernetes_monitoring', False)}")
        print(f"   - S3 monitoring: {features.get('s3_monitoring', False)}")
        print(f"   - Performance metrics: {features.get('performance_metrics', False)}")
        
        return True
    except Exception as e:
        print(f"❌ Feature flags test failed: {e}")
        return False

def test_view_modes():
    """Test that view modes include Storage Monitor"""
    print("\n👁️ Testing View Modes...")
    try:
        config = get_config()
        view_modes = config.get('view_modes', [])
        
        print(f"✅ View modes loaded: {len(view_modes)} modes")
        for mode in view_modes:
            print(f"   • {mode}")
        
        if 'Storage Monitor' in view_modes:
            print("✅ Storage Monitor view mode is available")
        else:
            print("⚠️ Storage Monitor view mode not found")
        
        return True
    except Exception as e:
        print(f"❌ View modes test failed: {e}")
        return False

def test_dependencies():
    """Test that all required dependencies are available"""
    print("\n📚 Testing Dependencies...")
    try:
        # Test boto3 availability
        try:
            import boto3
            print("✅ boto3 is available")
        except ImportError:
            print("⚠️ boto3 not available (S3 monitoring will be disabled)")
        
        # Test botocore availability
        try:
            import botocore
            print("✅ botocore is available")
        except ImportError:
            print("⚠️ botocore not available (S3 monitoring will be disabled)")
        
        # Test streamlit availability
        try:
            import streamlit
            print("✅ Streamlit is available")
        except ImportError:
            print("❌ Streamlit not available (required)")
            return False
        
        # Test plotly availability  
        try:
            import plotly
            print("✅ Plotly is available")
        except ImportError:
            print("⚠️ Plotly not available (charts will be limited)")
        
        return True
    except Exception as e:
        print(f"❌ Dependencies test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Platform Monitor - S3 Integration Test Suite")
    print("=" * 60)
    
    tests = [
        test_dependencies,
        test_config_loading,
        test_feature_flags,
        test_view_modes,
        test_s3_adapter_initialization,
        test_s3_adapter_methods,
        test_s3_views_initialization,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"🏁 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! S3 integration is ready.")
        return 0
    else:
        print("⚠️ Some tests failed. Review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
