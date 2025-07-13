#!/usr/bin/env python3
"""Configuration and integration utilities for development checker systems.

This module provides configuration management and integration utilities
for the original development_checker.py and the enhanced comprehensive
quality assurance system.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, TypedDict
from dataclasses import dataclass

# Add src to path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger


class QualityCheckConfig(TypedDict):
    """Configuration for quality checks."""
    enabled: bool
    priority: str  # "high", "medium", "low"
    timeout: int  # seconds
    retry_count: int
    fail_fast: bool


class DevelopmentCheckerConfig:
    """Configuration manager for development checker systems."""
    
    def __init__(self, config_file: Optional[Path] = None) -> None:
        """Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (auto-detected if None)
        """
        self.logger = AstolfoLogger(__name__)
        
        if config_file is None:
            config_file = Path(__file__).parent / "development_checker_config.json"
        
        self.config_file = config_file
        self.project_root = Path(__file__).parent.parent
        
        # Default configuration
        self.default_config = {
            "development_checks": {
                "utc_timestamp_leaks": {
                    "enabled": True,
                    "priority": "high",
                    "timeout": 30,
                    "retry_count": 1,
                    "fail_fast": True
                },
                "timestamp_test_coverage": {
                    "enabled": True,
                    "priority": "high",
                    "timeout": 30,
                    "retry_count": 1,
                    "fail_fast": True
                },
                "realtime_timestamp_tests": {
                    "enabled": True,
                    "priority": "high",
                    "timeout": 60,
                    "retry_count": 1,
                    "fail_fast": True
                },
                "import_consistency": {
                    "enabled": True,
                    "priority": "high",
                    "timeout": 30,
                    "retry_count": 1,
                    "fail_fast": True
                }
            },
            "comprehensive_qa": {
                "enabled": True,
                "auto_fallback": True,
                "quality_gates": {
                    "level1_basic": {
                        "enabled": True,
                        "priority": "high",
                        "timeout": 120,
                        "retry_count": 1,
                        "fail_fast": True
                    },
                    "level2_functional": {
                        "enabled": True,
                        "priority": "high",
                        "timeout": 180,
                        "retry_count": 1,
                        "fail_fast": True
                    },
                    "level3_integration": {
                        "enabled": True,
                        "priority": "medium",
                        "timeout": 300,
                        "retry_count": 1,
                        "fail_fast": False
                    },
                    "level4_production": {
                        "enabled": False,  # Disabled by default due to complexity
                        "priority": "low",
                        "timeout": 600,
                        "retry_count": 1,
                        "fail_fast": False
                    }
                },
                "category_checkers": {
                    "discord_integration": {
                        "enabled": True,
                        "priority": "high",
                        "timeout": 120,
                        "retry_count": 1,
                        "fail_fast": False
                    },
                    "content_processing": {
                        "enabled": True,
                        "priority": "high",
                        "timeout": 120,
                        "retry_count": 1,
                        "fail_fast": False
                    },
                    "data_management": {
                        "enabled": True,
                        "priority": "high",
                        "timeout": 120,
                        "retry_count": 1,
                        "fail_fast": False
                    },
                    "quality_validation": {
                        "enabled": True,
                        "priority": "medium",
                        "timeout": 120,
                        "retry_count": 1,
                        "fail_fast": False
                    },
                    "integration_control": {
                        "enabled": True,
                        "priority": "medium",
                        "timeout": 120,
                        "retry_count": 1,
                        "fail_fast": False
                    }
                },
                "automation_checkers": {
                    "instant_checker": {
                        "enabled": True,
                        "priority": "high",
                        "timeout": 30,
                        "retry_count": 1,
                        "fail_fast": False
                    },
                    "category_checker": {
                        "enabled": True,
                        "priority": "medium",
                        "timeout": 180,
                        "retry_count": 1,
                        "fail_fast": False
                    },
                    "comprehensive_checker": {
                        "enabled": False,  # Very comprehensive, disabled by default
                        "priority": "low",
                        "timeout": 900,
                        "retry_count": 1,
                        "fail_fast": False
                    }
                }
            },
            "execution": {
                "parallel_execution": True,
                "max_concurrent_checks": 5,
                "global_timeout": 1800,  # 30 minutes
                "log_level": "INFO",
                "save_reports": True,
                "report_directory": "quality_reports"
            },
            "thresholds": {
                "minimum_pass_rate": 80.0,  # Minimum pass rate to consider acceptable
                "minimum_quality_score": 75.0,  # Minimum average quality score
                "critical_check_failure_threshold": 0,  # Number of critical check failures allowed
                "warning_threshold": 10  # Maximum warnings before flagging
            }
        }
        
        self.config = self.load_config()
        
        self.logger.info(
            "Development checker config initialized",
            context={
                "config_file": str(self.config_file),
                "comprehensive_qa_enabled": self.is_comprehensive_qa_enabled()
            }
        )
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        if self.config_file.exists():
            try:
                import json
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                
                # Merge with defaults
                config = self.default_config.copy()
                config.update(file_config)
                
                self.logger.info(f"Configuration loaded from {self.config_file}")
                return config
                
            except Exception as e:
                self.logger.warning(f"Failed to load config from {self.config_file}: {e}")
                self.logger.info("Using default configuration")
        
        return self.default_config.copy()
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            import json
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save config to {self.config_file}: {e}")
    
    def is_comprehensive_qa_enabled(self) -> bool:
        """Check if comprehensive QA is enabled."""
        return self.config.get("comprehensive_qa", {}).get("enabled", True)
    
    def get_check_config(self, category: str, check_name: str) -> Optional[QualityCheckConfig]:
        """Get configuration for a specific check.
        
        Args:
            category: Category of the check (e.g., "development_checks", "quality_gates")
            check_name: Name of the specific check
            
        Returns:
            Configuration for the check or None if not found
        """
        category_config = self.config.get(category, {})
        check_config = category_config.get(check_name, {})
        
        if not check_config:
            return None
        
        return QualityCheckConfig(
            enabled=check_config.get("enabled", True),
            priority=check_config.get("priority", "medium"),
            timeout=check_config.get("timeout", 60),
            retry_count=check_config.get("retry_count", 1),
            fail_fast=check_config.get("fail_fast", False)
        )
    
    def get_enabled_development_checks(self) -> List[str]:
        """Get list of enabled development checks."""
        dev_checks = self.config.get("development_checks", {})
        return [name for name, config in dev_checks.items() if config.get("enabled", True)]
    
    def get_enabled_quality_gates(self) -> List[str]:
        """Get list of enabled quality gates."""
        if not self.is_comprehensive_qa_enabled():
            return []
        
        gates = self.config.get("comprehensive_qa", {}).get("quality_gates", {})
        return [name for name, config in gates.items() if config.get("enabled", True)]
    
    def get_enabled_category_checkers(self) -> List[str]:
        """Get list of enabled category checkers."""
        if not self.is_comprehensive_qa_enabled():
            return []
        
        checkers = self.config.get("comprehensive_qa", {}).get("category_checkers", {})
        return [name for name, config in checkers.items() if config.get("enabled", True)]
    
    def get_enabled_automation_checkers(self) -> List[str]:
        """Get list of enabled automation checkers."""
        if not self.is_comprehensive_qa_enabled():
            return []
        
        checkers = self.config.get("comprehensive_qa", {}).get("automation_checkers", {})
        return [name for name, config in checkers.items() if config.get("enabled", True)]
    
    def should_fail_fast(self, category: str, check_name: str) -> bool:
        """Check if a specific check should fail fast."""
        check_config = self.get_check_config(category, check_name)
        return check_config.get("fail_fast", False) if check_config else False
    
    def get_execution_config(self) -> Dict[str, Any]:
        """Get execution configuration."""
        return self.config.get("execution", {})
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get quality thresholds."""
        return self.config.get("thresholds", {})
    
    def meets_quality_thresholds(self, results: List[Dict[str, Any]]) -> bool:
        """Check if results meet quality thresholds.
        
        Args:
            results: List of check results
            
        Returns:
            True if all thresholds are met
        """
        if not results:
            return False
        
        thresholds = self.get_thresholds()
        
        # Calculate metrics
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.get("passed", False))
        pass_rate = (passed_checks / total_checks) * 100
        
        avg_quality_score = 0
        if "quality_score" in results[0]:  # Enhanced results
            avg_quality_score = sum(r.get("quality_score", 0) for r in results) / total_checks
        
        critical_failures = sum(1 for r in results 
                              if not r.get("passed", False) and 
                              r.get("priority", "medium") == "high")
        
        total_warnings = sum(len(r.get("warnings", [])) for r in results)
        
        # Check thresholds
        min_pass_rate = thresholds.get("minimum_pass_rate", 80.0)
        min_quality_score = thresholds.get("minimum_quality_score", 75.0)
        max_critical_failures = thresholds.get("critical_check_failure_threshold", 0)
        max_warnings = thresholds.get("warning_threshold", 10)
        
        meets_pass_rate = pass_rate >= min_pass_rate
        meets_quality_score = avg_quality_score >= min_quality_score or avg_quality_score == 0
        meets_critical_threshold = critical_failures <= max_critical_failures
        meets_warning_threshold = total_warnings <= max_warnings
        
        self.logger.info(
            "Quality threshold evaluation",
            context={
                "pass_rate": pass_rate,
                "min_pass_rate": min_pass_rate,
                "meets_pass_rate": meets_pass_rate,
                "avg_quality_score": avg_quality_score,
                "min_quality_score": min_quality_score,
                "meets_quality_score": meets_quality_score,
                "critical_failures": critical_failures,
                "max_critical_failures": max_critical_failures,
                "meets_critical_threshold": meets_critical_threshold,
                "total_warnings": total_warnings,
                "max_warnings": max_warnings,
                "meets_warning_threshold": meets_warning_threshold
            }
        )
        
        return all([
            meets_pass_rate,
            meets_quality_score,
            meets_critical_threshold,
            meets_warning_threshold
        ])
    
    def get_environment_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables."""
        overrides = {}
        
        # Check for environment variable overrides
        env_prefix = "DEVCHECKER_"
        
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                config_key = key[len(env_prefix):].lower()
                
                # Convert string values to appropriate types
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)
                elif "." in value and value.replace(".", "").isdigit():
                    value = float(value)
                
                overrides[config_key] = value
        
        return overrides
    
    def apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        overrides = self.get_environment_overrides()
        
        if overrides:
            self.logger.info(f"Applying environment overrides: {overrides}")
            
            # Apply simple overrides
            for key, value in overrides.items():
                if key == "comprehensive_qa_enabled":
                    self.config["comprehensive_qa"]["enabled"] = value
                elif key == "parallel_execution":
                    self.config["execution"]["parallel_execution"] = value
                elif key == "max_concurrent_checks":
                    self.config["execution"]["max_concurrent_checks"] = value
                elif key == "global_timeout":
                    self.config["execution"]["global_timeout"] = value
                elif key == "log_level":
                    self.config["execution"]["log_level"] = value
                elif key == "minimum_pass_rate":
                    self.config["thresholds"]["minimum_pass_rate"] = value
                elif key == "minimum_quality_score":
                    self.config["thresholds"]["minimum_quality_score"] = value
    
    def create_default_config_file(self) -> None:
        """Create default configuration file."""
        if not self.config_file.exists():
            self.save_config()
            self.logger.info(f"Created default configuration file: {self.config_file}")
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of integration between original and enhanced systems."""
        status = {
            "original_system": {
                "available": True,  # Always available
                "checks_enabled": len(self.get_enabled_development_checks()),
                "total_checks": len(self.config.get("development_checks", {}))
            },
            "enhanced_system": {
                "available": False,
                "comprehensive_qa_enabled": self.is_comprehensive_qa_enabled(),
                "quality_gates_enabled": 0,
                "category_checkers_enabled": 0,
                "automation_checkers_enabled": 0
            },
            "integration": {
                "config_file_exists": self.config_file.exists(),
                "environment_overrides": len(self.get_environment_overrides()),
                "auto_fallback_enabled": self.config.get("comprehensive_qa", {}).get("auto_fallback", True)
            }
        }
        
        # Check if enhanced system is available
        try:
            from utils.development_checker_enhanced import EnhancedDevelopmentChecker
            status["enhanced_system"]["available"] = True
            status["enhanced_system"]["quality_gates_enabled"] = len(self.get_enabled_quality_gates())
            status["enhanced_system"]["category_checkers_enabled"] = len(self.get_enabled_category_checkers())
            status["enhanced_system"]["automation_checkers_enabled"] = len(self.get_enabled_automation_checkers())
        except ImportError:
            pass
        
        return status


# Global configuration instance
_config_instance = None

def get_config() -> DevelopmentCheckerConfig:
    """Get global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = DevelopmentCheckerConfig()
        _config_instance.apply_environment_overrides()
    return _config_instance


def main():
    """Configuration utility main function."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Development Checker Configuration Utility")
    parser.add_argument("--create-default", action="store_true",
                       help="Create default configuration file")
    parser.add_argument("--status", action="store_true",
                       help="Show integration status")
    parser.add_argument("--validate", action="store_true",
                       help="Validate current configuration")
    
    args = parser.parse_args()
    
    config = get_config()
    
    if args.create_default:
        config.create_default_config_file()
        print(f"✅ Default configuration created: {config.config_file}")
    
    if args.status:
        status = config.get_integration_status()
        print("📊 Development Checker Integration Status:")
        print(json.dumps(status, indent=2))
    
    if args.validate:
        # Basic validation
        enabled_dev_checks = len(config.get_enabled_development_checks())
        enabled_qa_gates = len(config.get_enabled_quality_gates())
        
        print("✅ Configuration validation:")
        print(f"  • Development checks enabled: {enabled_dev_checks}")
        print(f"  • Quality gates enabled: {enabled_qa_gates}")
        print(f"  • Comprehensive QA enabled: {config.is_comprehensive_qa_enabled()}")
        
        if enabled_dev_checks == 0:
            print("⚠️  Warning: No development checks enabled")
        
        if config.is_comprehensive_qa_enabled() and enabled_qa_gates == 0:
            print("⚠️  Warning: Comprehensive QA enabled but no quality gates enabled")


if __name__ == "__main__":
    main()