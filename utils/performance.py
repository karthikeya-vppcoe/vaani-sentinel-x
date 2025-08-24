"""
Performance monitoring utilities for Vaani Sentinel X.
Production-ready performance tracking and optimization.
"""

import time
import psutil
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_usage_percent: float
    process_count: int
    execution_time: Optional[float] = None
    operation_name: Optional[str] = None


class PerformanceMonitor:
    """Monitor system and application performance."""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history = 1000  # Keep last 1000 metrics
        self._lock = threading.Lock()
    
    def collect_system_metrics(self) -> PerformanceMetrics:
        """Collect current system performance metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return PerformanceMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_mb=memory.used / 1024 / 1024,
            disk_usage_percent=disk.percent,
            process_count=len(psutil.pids())
        )
    
    def record_metrics(self, metrics: PerformanceMetrics) -> None:
        """Record performance metrics."""
        with self._lock:
            self.metrics_history.append(metrics)
            
            # Keep only recent metrics
            if len(self.metrics_history) > self.max_history:
                self.metrics_history = self.metrics_history[-self.max_history:]
    
    @contextmanager
    def measure_execution_time(self, operation_name: str):
        """Context manager to measure execution time."""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            
            # Collect system metrics with execution time
            metrics = self.collect_system_metrics()
            metrics.execution_time = execution_time
            metrics.operation_name = operation_name
            
            self.record_metrics(metrics)
    
    def get_recent_metrics(self, count: int = 10) -> List[PerformanceMetrics]:
        """Get recent performance metrics."""
        with self._lock:
            return self.metrics_history[-count:] if self.metrics_history else []
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        with self._lock:
            if not self.metrics_history:
                return {'status': 'no_data', 'message': 'No performance data available'}
            
            recent_metrics = self.metrics_history[-10:]  # Last 10 measurements
            
            # Calculate averages
            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
            avg_disk = sum(m.disk_usage_percent for m in recent_metrics) / len(recent_metrics)
            
            # Calculate execution times
            execution_times = [m.execution_time for m in recent_metrics if m.execution_time is not None]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            # Determine system health
            health_issues = []
            if avg_cpu > 80:
                health_issues.append("High CPU usage")
            if avg_memory > 80:
                health_issues.append("High memory usage")
            if avg_disk > 90:
                health_issues.append("High disk usage")
            if avg_execution_time > 10:
                health_issues.append("Slow operation execution")
            
            return {
                'status': 'healthy' if not health_issues else 'warning',
                'issues': health_issues,
                'metrics': {
                    'avg_cpu_percent': round(avg_cpu, 2),
                    'avg_memory_percent': round(avg_memory, 2),
                    'avg_disk_percent': round(avg_disk, 2),
                    'avg_execution_time': round(avg_execution_time, 3),
                    'total_measurements': len(self.metrics_history),
                    'latest_timestamp': recent_metrics[-1].timestamp if recent_metrics else None
                }
            }


class ResourceManager:
    """Manage system resources and limits."""
    
    @staticmethod
    def check_available_memory() -> Dict[str, float]:
        """Check available system memory."""
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total / 1024 / 1024 / 1024,
            'available_gb': memory.available / 1024 / 1024 / 1024,
            'used_percent': memory.percent,
            'free_gb': memory.free / 1024 / 1024 / 1024
        }
    
    @staticmethod
    def check_disk_space(path: str = '/') -> Dict[str, float]:
        """Check available disk space."""
        disk = psutil.disk_usage(path)
        return {
            'total_gb': disk.total / 1024 / 1024 / 1024,
            'used_gb': disk.used / 1024 / 1024 / 1024,
            'free_gb': disk.free / 1024 / 1024 / 1024,
            'used_percent': (disk.used / disk.total) * 100
        }
    
    @staticmethod
    def check_system_load() -> Dict[str, float]:
        """Check system load averages."""
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
        cpu_count = psutil.cpu_count()
        
        return {
            'load_1min': load_avg[0],
            'load_5min': load_avg[1],
            'load_15min': load_avg[2],
            'cpu_count': cpu_count,
            'load_per_cpu': load_avg[0] / cpu_count if cpu_count > 0 else 0
        }
    
    @staticmethod
    def get_resource_recommendations() -> List[str]:
        """Get resource optimization recommendations."""
        recommendations = []
        
        memory_info = ResourceManager.check_available_memory()
        disk_info = ResourceManager.check_disk_space()
        load_info = ResourceManager.check_system_load()
        
        if memory_info['used_percent'] > 80:
            recommendations.append("Consider increasing system memory or optimizing memory usage")
        
        if disk_info['used_percent'] > 85:
            recommendations.append("Disk space is running low, consider cleanup or expansion")
        
        if load_info['load_per_cpu'] > 1.0:
            recommendations.append("System load is high, consider optimizing processes or scaling")
        
        if memory_info['total_gb'] < 2:
            recommendations.append("System has less than 2GB RAM, consider increasing memory")
        
        return recommendations


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor