#!/usr/bin/env python3
"""
Production Readiness Validation Script for Vaani Sentinel X.
Comprehensive checks for deployment readiness.
"""

import os
import sys
import subprocess
from typing import Dict, List, Tuple, Any

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import get_config
from utils.common import setup_logger, HealthChecker
from utils.security import SecurityManager, SecurityAudit
from utils.performance import ResourceManager


class ProductionReadinessChecker:
    """Comprehensive production readiness validation."""
    
    def __init__(self):
        self.config = get_config()
        self.logger = setup_logger('production_checker', 'production_checker_user')
        self.health_checker = HealthChecker()
        self.checks_passed = 0
        self.total_checks = 0
    
    def check_dependencies(self) -> bool:
        """Check all required dependencies are installed."""
        print("📦 Checking Dependencies...")
        self.total_checks += 1
        
        health_status = self.health_checker.check_dependencies()
        missing_deps = [dep for dep, status in health_status.items() if not status]
        
        if missing_deps:
            print(f"   ✗ Missing dependencies: {missing_deps}")
            print("   → Run: pip install -r requirements.txt")
            return False
        else:
            print("   ✓ All dependencies installed")
            self.checks_passed += 1
            return True
    
    def check_configuration(self) -> bool:
        """Check configuration completeness."""
        print("⚙️  Checking Configuration...")
        self.total_checks += 1
        
        issues = []
        
        # Check required API keys for production
        if self.config.environment == "production":
            if not self.config.apis.groq_api_key:
                issues.append("GROQ_API_KEY not set")
            if not self.config.security.jwt_secret or len(self.config.security.jwt_secret) < 32:
                issues.append("JWT_SECRET not set or too short (minimum 32 characters)")
            if not self.config.web.secret_key or len(self.config.web.secret_key) < 32:
                issues.append("SECRET_KEY not set or too short (minimum 32 characters)")
        
        # Check directory structure
        health_status = self.health_checker.check_directories()
        missing_dirs = [dir_name for dir_name, status in health_status.items() if not status]
        if missing_dirs:
            issues.append(f"Missing directories: {missing_dirs}")
        
        # Check config files
        config_status = self.health_checker.check_config_files()
        missing_configs = [file_name for file_name, status in config_status.items() if not status]
        if missing_configs:
            issues.append(f"Missing config files: {missing_configs}")
        
        if issues:
            print(f"   ✗ Configuration issues:")
            for issue in issues:
                print(f"     - {issue}")
            return False
        else:
            print("   ✓ Configuration complete")
            self.checks_passed += 1
            return True
    
    def check_agents(self) -> bool:
        """Check all agents are functional."""
        print("🤖 Checking Agents...")
        self.total_checks += 1
        
        # Run agent test script
        try:
            result = subprocess.run(
                [sys.executable, 'scripts/test_agents.py'],
                cwd=self.config.directories.root_dir,
                capture_output=True,
                text=True,
                timeout=180
            )
            
            if result.returncode == 0:
                print("   ✓ All agents tested successfully")
                self.checks_passed += 1
                return True
            else:
                print("   ✗ Some agents failed testing")
                print(f"   → Check logs for details")
                return False
                
        except subprocess.TimeoutExpired:
            print("   ✗ Agent testing timed out")
            return False
        except Exception as e:
            print(f"   ✗ Agent testing failed: {e}")
            return False
    
    def check_security(self) -> bool:
        """Check security configuration."""
        print("🔒 Checking Security...")
        self.total_checks += 1
        
        issues = []
        
        # Check file permissions
        sensitive_files = SecurityAudit.scan_sensitive_files(str(self.config.directories.root_dir))
        if sensitive_files:
            issues.append(f"Insecure file permissions: {len(sensitive_files)} files")
        
        # Check if .env file has secure permissions
        env_file = self.config.directories.root_dir / '.env'
        if env_file.exists():
            env_audit = SecurityAudit.audit_file_permissions(str(env_file))
            if not env_audit.get('secure', False):
                issues.append(".env file has insecure permissions")
        
        # Check secrets management
        if self.config.environment == "production":
            if not self.config.security.encryption_key:
                issues.append("Encryption key not configured")
        
        if issues:
            print(f"   ✗ Security issues:")
            for issue in issues:
                print(f"     - {issue}")
            print("   → Fix permissions: chmod 600 .env")
            return False
        else:
            print("   ✓ Security configuration verified")
            self.checks_passed += 1
            return True
    
    def check_performance(self) -> bool:
        """Check system performance requirements."""
        print("⚡ Checking Performance...")
        self.total_checks += 1
        
        issues = []
        
        # Check system resources
        memory_info = ResourceManager.check_available_memory()
        disk_info = ResourceManager.check_disk_space(str(self.config.directories.root_dir))
        
        if memory_info['total_gb'] < 1:
            issues.append(f"Low memory: {memory_info['total_gb']:.1f}GB (recommended: 2GB+)")
        
        if disk_info['free_gb'] < 1:
            issues.append(f"Low disk space: {disk_info['free_gb']:.1f}GB (recommended: 5GB+)")
        
        if memory_info['used_percent'] > 90:
            issues.append(f"High memory usage: {memory_info['used_percent']:.1f}%")
        
        if disk_info['used_percent'] > 95:
            issues.append(f"High disk usage: {disk_info['used_percent']:.1f}%")
        
        # Get recommendations
        recommendations = ResourceManager.get_resource_recommendations()
        if recommendations:
            issues.extend(recommendations)
        
        if issues:
            print(f"   ⚠️  Performance warnings:")
            for issue in issues:
                print(f"     - {issue}")
            # Don't fail on performance warnings, just warn
            print("   → Consider addressing performance issues for optimal operation")
        
        print("   ✓ Performance check completed")
        self.checks_passed += 1
        return True
    
    def check_docker(self) -> bool:
        """Check Docker configuration."""
        print("🐳 Checking Docker...")
        self.total_checks += 1
        
        issues = []
        
        # Check if Docker is available
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                issues.append("Docker not available")
        except FileNotFoundError:
            issues.append("Docker not installed")
        except subprocess.TimeoutExpired:
            issues.append("Docker check timed out")
        
        # Check if docker-compose is available
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                issues.append("Docker Compose not available")
        except FileNotFoundError:
            issues.append("Docker Compose not installed")
        except subprocess.TimeoutExpired:
            issues.append("Docker Compose check timed out")
        
        # Validate docker-compose.yml
        if not (self.config.directories.root_dir / 'docker-compose.yml').exists():
            issues.append("docker-compose.yml not found")
        
        # Validate Dockerfile
        if not (self.config.directories.root_dir / 'Dockerfile').exists():
            issues.append("Dockerfile not found")
        
        if issues:
            print(f"   ✗ Docker issues:")
            for issue in issues:
                print(f"     - {issue}")
            return False
        else:
            print("   ✓ Docker configuration verified")
            self.checks_passed += 1
            return True
    
    def run_all_checks(self) -> bool:
        """Run all production readiness checks."""
        print("🚀 VAANI SENTINEL X - PRODUCTION READINESS CHECK")
        print("=" * 60)
        
        # Run all checks
        checks = [
            self.check_dependencies,
            self.check_configuration,
            self.check_agents,
            self.check_security,
            self.check_performance,
            self.check_docker,
        ]
        
        all_passed = True
        for check in checks:
            try:
                if not check():
                    all_passed = False
            except Exception as e:
                print(f"   ✗ Check failed with error: {e}")
                all_passed = False
            print()  # Add spacing
        
        # Final summary
        print("=" * 60)
        print(f"SUMMARY: {self.checks_passed}/{self.total_checks} checks passed")
        
        if all_passed and self.checks_passed == self.total_checks:
            print("🎉 SYSTEM IS PRODUCTION READY!")
            print("\nNext steps:")
            print("  1. Deploy: ./scripts/deploy.sh")
            print("  2. Monitor: docker-compose logs -f")
            print("  3. Health check: curl http://localhost/health")
        else:
            print("⚠️  SYSTEM NOT READY - Fix issues above before deployment")
            print("\nRecommended actions:")
            print("  1. Fix configuration issues")
            print("  2. Install missing dependencies")
            print("  3. Verify agent functionality")
            print("  4. Re-run this check")
        
        print("=" * 60)
        return all_passed and self.checks_passed == self.total_checks


def main():
    """Main function for production readiness check."""
    checker = ProductionReadinessChecker()
    ready = checker.run_all_checks()
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()