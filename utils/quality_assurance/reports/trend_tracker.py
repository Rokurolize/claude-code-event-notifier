#!/usr/bin/env python3
"""Trend Tracker.

This module provides comprehensive trend tracking functionality including:
- Quality trend analysis over time
- Performance trend monitoring and prediction
- Coverage trend tracking and forecasting
- Issue trend analysis and pattern detection
- Regression detection and early warning systems
- Improvement trend validation and measurement
- Comparative trend analysis across components
- Predictive analytics for quality forecasting
"""

import asyncio
import json
import time
import sys
import os
import statistics
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import sqlite3
import numpy as np
from scipy import stats
import pandas as pd

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker


# Trend Analysis Types
@dataclass
class TrendDataPoint:
    """Single data point in a trend."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    category: str = "general"


@dataclass
class TrendAnalysis:
    """Analysis results for a trend."""
    metric_name: str
    data_points: List[TrendDataPoint]
    trend_direction: str  # "increasing", "decreasing", "stable", "volatile"
    trend_strength: float  # 0-1, confidence in trend direction
    slope: float  # Rate of change
    correlation_coefficient: float
    volatility: float
    forecast: List[float]  # Predicted future values
    statistical_significance: float
    anomalies: List[TrendDataPoint]
    change_points: List[datetime]  # Points where trend changed significantly
    
    
@dataclass  
class TrendComparison:
    """Comparison between multiple trends."""
    trend_names: List[str]
    correlation_matrix: Dict[str, Dict[str, float]]
    synchronized_periods: List[Tuple[datetime, datetime]]
    divergence_points: List[datetime]
    comparative_analysis: Dict[str, Any]


@dataclass
class TrendAlert:
    """Alert for significant trend changes."""
    alert_id: str
    metric_name: str
    alert_type: str  # "regression", "improvement", "anomaly", "threshold"
    severity: str  # "low", "medium", "high", "critical"
    triggered_at: datetime
    description: str
    current_value: float
    threshold_value: Optional[float]
    trend_data: TrendAnalysis
    recommended_actions: List[str]


@dataclass
class TrendReport:
    """Comprehensive trend report."""
    report_id: str
    generated_at: datetime
    time_period: Tuple[datetime, datetime]
    analyzed_metrics: List[str]
    trend_analyses: Dict[str, TrendAnalysis]
    trend_comparisons: List[TrendComparison]
    active_alerts: List[TrendAlert]
    summary: Dict[str, Any]
    predictions: Dict[str, List[float]]
    recommendations: List[str]


class TrendDatabase:
    """Database manager for trend data storage."""
    
    def __init__(self, db_path: Path = None):
        self.logger = AstolfoLogger(__name__)
        self.db_path = db_path or Path("trend_data.db")
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the trend database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create tables
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trend_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        value REAL NOT NULL,
                        source TEXT DEFAULT 'unknown',
                        category TEXT DEFAULT 'general',
                        metadata TEXT DEFAULT '{}',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trend_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alert_id TEXT UNIQUE NOT NULL,
                        metric_name TEXT NOT NULL,
                        alert_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        triggered_at DATETIME NOT NULL,
                        description TEXT NOT NULL,
                        current_value REAL NOT NULL,
                        threshold_value REAL,
                        resolved_at DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trend_data_metric_time 
                    ON trend_data(metric_name, timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trend_alerts_metric 
                    ON trend_alerts(metric_name, triggered_at)
                """)
                
                conn.commit()
                self.logger.debug("Trend database initialized")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize trend database: {e}")
            raise
    
    async def store_data_point(self, data_point: TrendDataPoint) -> None:
        """Store a single trend data point."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO trend_data 
                    (metric_name, timestamp, value, source, category, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    data_point.metadata.get('metric_name', 'unknown'),
                    data_point.timestamp.isoformat(),
                    data_point.value,
                    data_point.source,
                    data_point.category,
                    json.dumps(data_point.metadata)
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to store trend data point: {e}")
    
    async def store_data_points(self, data_points: List[TrendDataPoint]) -> None:
        """Store multiple trend data points."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                data_tuples = [
                    (
                        dp.metadata.get('metric_name', 'unknown'),
                        dp.timestamp.isoformat(),
                        dp.value,
                        dp.source,
                        dp.category,
                        json.dumps(dp.metadata)
                    )
                    for dp in data_points
                ]
                
                cursor.executemany("""
                    INSERT INTO trend_data 
                    (metric_name, timestamp, value, source, category, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, data_tuples)
                
                conn.commit()
                self.logger.debug(f"Stored {len(data_points)} trend data points")
                
        except Exception as e:
            self.logger.error(f"Failed to store trend data points: {e}")
    
    async def get_trend_data(
        self,
        metric_name: str,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = None
    ) -> List[TrendDataPoint]:
        """Retrieve trend data for a metric."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT timestamp, value, source, category, metadata FROM trend_data WHERE metric_name = ?"
                params = [metric_name]
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time.isoformat())
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time.isoformat())
                
                query += " ORDER BY timestamp ASC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                data_points = []
                for row in rows:
                    timestamp_str, value, source, category, metadata_str = row
                    
                    timestamp = datetime.fromisoformat(timestamp_str)
                    metadata = json.loads(metadata_str) if metadata_str else {}
                    
                    data_point = TrendDataPoint(
                        timestamp=timestamp,
                        value=value,
                        metadata=metadata,
                        source=source,
                        category=category
                    )
                    data_points.append(data_point)
                
                return data_points
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve trend data for {metric_name}: {e}")
            return []
    
    async def store_alert(self, alert: TrendAlert) -> None:
        """Store a trend alert."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO trend_alerts 
                    (alert_id, metric_name, alert_type, severity, triggered_at, 
                     description, current_value, threshold_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.alert_id,
                    alert.metric_name,
                    alert.alert_type,
                    alert.severity,
                    alert.triggered_at.isoformat(),
                    alert.description,
                    alert.current_value,
                    alert.threshold_value
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to store trend alert: {e}")
    
    async def get_active_alerts(self, metric_name: str = None) -> List[Dict[str, Any]]:
        """Get active alerts."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT alert_id, metric_name, alert_type, severity, triggered_at,
                           description, current_value, threshold_value
                    FROM trend_alerts 
                    WHERE resolved_at IS NULL
                """
                params = []
                
                if metric_name:
                    query += " AND metric_name = ?"
                    params.append(metric_name)
                
                query += " ORDER BY triggered_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                alerts = []
                for row in rows:
                    alert_data = {
                        'alert_id': row[0],
                        'metric_name': row[1],
                        'alert_type': row[2],
                        'severity': row[3],
                        'triggered_at': datetime.fromisoformat(row[4]),
                        'description': row[5],
                        'current_value': row[6],
                        'threshold_value': row[7]
                    }
                    alerts.append(alert_data)
                
                return alerts
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve active alerts: {e}")
            return []


class TrendAnalyzer:
    """Analyzes trends in time series data."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
    
    async def analyze_trend(
        self,
        data_points: List[TrendDataPoint],
        metric_name: str
    ) -> TrendAnalysis:
        """Analyze trend for a series of data points."""
        
        if len(data_points) < 3:
            # Not enough data for meaningful analysis
            return TrendAnalysis(
                metric_name=metric_name,
                data_points=data_points,
                trend_direction="insufficient_data",
                trend_strength=0.0,
                slope=0.0,
                correlation_coefficient=0.0,
                volatility=0.0,
                forecast=[],
                statistical_significance=0.0,
                anomalies=[],
                change_points=[]
            )
        
        # Extract values and timestamps
        values = [dp.value for dp in data_points]
        timestamps = [(dp.timestamp - data_points[0].timestamp).total_seconds() for dp in data_points]
        
        # Calculate basic statistics
        slope, correlation_coefficient = await self._calculate_trend_metrics(timestamps, values)
        volatility = await self._calculate_volatility(values)
        trend_direction = await self._determine_trend_direction(slope, correlation_coefficient)
        trend_strength = abs(correlation_coefficient)
        statistical_significance = await self._calculate_statistical_significance(timestamps, values)
        
        # Detect anomalies
        anomalies = await self._detect_anomalies(data_points, values)
        
        # Detect change points
        change_points = await self._detect_change_points(data_points, values)
        
        # Generate forecast
        forecast = await self._generate_forecast(timestamps, values)
        
        return TrendAnalysis(
            metric_name=metric_name,
            data_points=data_points,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            slope=slope,
            correlation_coefficient=correlation_coefficient,
            volatility=volatility,
            forecast=forecast,
            statistical_significance=statistical_significance,
            anomalies=anomalies,
            change_points=change_points
        )
    
    async def _calculate_trend_metrics(
        self, 
        timestamps: List[float], 
        values: List[float]
    ) -> Tuple[float, float]:
        """Calculate slope and correlation coefficient."""
        try:
            if len(timestamps) < 2:
                return 0.0, 0.0
            
            # Linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(timestamps, values)
            
            return slope, r_value
            
        except Exception as e:
            self.logger.debug(f"Error calculating trend metrics: {e}")
            return 0.0, 0.0
    
    async def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (coefficient of variation)."""
        try:
            if len(values) < 2:
                return 0.0
            
            mean_val = statistics.mean(values)
            if mean_val == 0:
                return 0.0
            
            std_dev = statistics.stdev(values)
            volatility = std_dev / abs(mean_val)
            
            return volatility
            
        except Exception as e:
            self.logger.debug(f"Error calculating volatility: {e}")
            return 0.0
    
    async def _determine_trend_direction(self, slope: float, correlation: float) -> str:
        """Determine overall trend direction."""
        correlation_threshold = 0.3
        slope_threshold = 0.01
        
        if abs(correlation) < correlation_threshold:
            return "stable"
        elif correlation > correlation_threshold and slope > slope_threshold:
            return "increasing"
        elif correlation < -correlation_threshold and slope < -slope_threshold:
            return "decreasing"
        else:
            return "volatile"
    
    async def _calculate_statistical_significance(
        self, 
        timestamps: List[float], 
        values: List[float]
    ) -> float:
        """Calculate statistical significance of the trend."""
        try:
            if len(timestamps) < 3:
                return 0.0
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(timestamps, values)
            
            # Convert p-value to significance score (lower p-value = higher significance)
            significance = max(0.0, 1.0 - p_value)
            
            return significance
            
        except Exception as e:
            self.logger.debug(f"Error calculating statistical significance: {e}")
            return 0.0
    
    async def _detect_anomalies(
        self, 
        data_points: List[TrendDataPoint], 
        values: List[float]
    ) -> List[TrendDataPoint]:
        """Detect anomalous data points using IQR method."""
        try:
            if len(values) < 4:
                return []
            
            # Calculate IQR
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1
            
            # Define outlier bounds
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            # Find anomalies
            anomalies = []
            for i, value in enumerate(values):
                if value < lower_bound or value > upper_bound:
                    anomalies.append(data_points[i])
            
            return anomalies
            
        except Exception as e:
            self.logger.debug(f"Error detecting anomalies: {e}")
            return []
    
    async def _detect_change_points(
        self, 
        data_points: List[TrendDataPoint], 
        values: List[float]
    ) -> List[datetime]:
        """Detect points where trend changes significantly."""
        try:
            if len(values) < 6:  # Need minimum data for change point detection
                return []
            
            change_points = []
            window_size = min(5, len(values) // 3)
            
            for i in range(window_size, len(values) - window_size):
                # Calculate slopes before and after point
                before_values = values[i-window_size:i]
                after_values = values[i:i+window_size]
                
                before_timestamps = list(range(len(before_values)))
                after_timestamps = list(range(len(after_values)))
                
                try:
                    slope_before, _, _, _, _ = stats.linregress(before_timestamps, before_values)
                    slope_after, _, _, _, _ = stats.linregress(after_timestamps, after_values)
                    
                    # Check if slopes differ significantly
                    slope_change = abs(slope_after - slope_before)
                    if slope_change > 0.1:  # Threshold for significant change
                        change_points.append(data_points[i].timestamp)
                        
                except:
                    continue
            
            return change_points
            
        except Exception as e:
            self.logger.debug(f"Error detecting change points: {e}")
            return []
    
    async def _generate_forecast(
        self, 
        timestamps: List[float], 
        values: List[float],
        periods: int = 5
    ) -> List[float]:
        """Generate simple linear forecast."""
        try:
            if len(timestamps) < 3:
                return []
            
            # Fit linear regression
            slope, intercept, _, _, _ = stats.linregress(timestamps, values)
            
            # Generate future timestamps
            last_timestamp = timestamps[-1]
            time_step = (timestamps[-1] - timestamps[0]) / (len(timestamps) - 1)
            
            forecast = []
            for i in range(1, periods + 1):
                future_timestamp = last_timestamp + (i * time_step)
                forecast_value = slope * future_timestamp + intercept
                forecast.append(forecast_value)
            
            return forecast
            
        except Exception as e:
            self.logger.debug(f"Error generating forecast: {e}")
            return []
    
    async def compare_trends(
        self, 
        trend_analyses: Dict[str, TrendAnalysis]
    ) -> List[TrendComparison]:
        """Compare multiple trends."""
        
        comparisons = []
        trend_names = list(trend_analyses.keys())
        
        if len(trend_names) < 2:
            return comparisons
        
        # Calculate correlation matrix
        correlation_matrix = {}
        for i, name1 in enumerate(trend_names):
            correlation_matrix[name1] = {}
            for j, name2 in enumerate(trend_names):
                if i == j:
                    correlation_matrix[name1][name2] = 1.0
                else:
                    correlation = await self._calculate_cross_correlation(
                        trend_analyses[name1], trend_analyses[name2]
                    )
                    correlation_matrix[name1][name2] = correlation
        
        # Find synchronized periods and divergence points
        synchronized_periods = await self._find_synchronized_periods(trend_analyses)
        divergence_points = await self._find_divergence_points(trend_analyses)
        
        # Generate comparative analysis
        comparative_analysis = await self._generate_comparative_analysis(trend_analyses)
        
        comparison = TrendComparison(
            trend_names=trend_names,
            correlation_matrix=correlation_matrix,
            synchronized_periods=synchronized_periods,
            divergence_points=divergence_points,
            comparative_analysis=comparative_analysis
        )
        
        comparisons.append(comparison)
        return comparisons
    
    async def _calculate_cross_correlation(
        self, 
        trend1: TrendAnalysis, 
        trend2: TrendAnalysis
    ) -> float:
        """Calculate correlation between two trends."""
        try:
            values1 = [dp.value for dp in trend1.data_points]
            values2 = [dp.value for dp in trend2.data_points]
            
            # Align data points by timestamp (simplified approach)
            min_length = min(len(values1), len(values2))
            values1 = values1[:min_length]
            values2 = values2[:min_length]
            
            if len(values1) < 2:
                return 0.0
            
            correlation, _ = stats.pearsonr(values1, values2)
            return correlation if not math.isnan(correlation) else 0.0
            
        except Exception as e:
            self.logger.debug(f"Error calculating cross correlation: {e}")
            return 0.0
    
    async def _find_synchronized_periods(
        self, 
        trend_analyses: Dict[str, TrendAnalysis]
    ) -> List[Tuple[datetime, datetime]]:
        """Find periods where trends move together."""
        # Simplified implementation
        return []
    
    async def _find_divergence_points(
        self, 
        trend_analyses: Dict[str, TrendAnalysis]
    ) -> List[datetime]:
        """Find points where trends diverge significantly."""
        # Simplified implementation
        return []
    
    async def _generate_comparative_analysis(
        self, 
        trend_analyses: Dict[str, TrendAnalysis]
    ) -> Dict[str, Any]:
        """Generate comparative analysis between trends."""
        
        analysis = {
            "strongest_trend": None,
            "most_volatile": None,
            "most_stable": None,
            "average_correlation": 0.0,
            "trend_summary": {}
        }
        
        # Find strongest trend (highest trend strength)
        strongest_name = max(
            trend_analyses.keys(),
            key=lambda name: trend_analyses[name].trend_strength
        )
        analysis["strongest_trend"] = strongest_name
        
        # Find most volatile
        most_volatile_name = max(
            trend_analyses.keys(),
            key=lambda name: trend_analyses[name].volatility
        )
        analysis["most_volatile"] = most_volatile_name
        
        # Find most stable (lowest volatility)
        most_stable_name = min(
            trend_analyses.keys(),
            key=lambda name: trend_analyses[name].volatility
        )
        analysis["most_stable"] = most_stable_name
        
        # Generate summary for each trend
        for name, trend in trend_analyses.items():
            analysis["trend_summary"][name] = {
                "direction": trend.trend_direction,
                "strength": trend.trend_strength,
                "volatility": trend.volatility,
                "data_points": len(trend.data_points)
            }
        
        return analysis


class TrendAlertManager:
    """Manages trend alerts and notifications."""
    
    def __init__(self, db: TrendDatabase):
        self.logger = AstolfoLogger(__name__)
        self.db = db
        self.alert_rules = self._load_default_alert_rules()
    
    def _load_default_alert_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load default alert rules."""
        return {
            "regression": {
                "threshold_change": -0.1,  # 10% decrease
                "min_data_points": 5,
                "severity": "high"
            },
            "volatility": {
                "threshold": 0.5,  # 50% volatility
                "min_data_points": 10,
                "severity": "medium"
            },
            "anomaly": {
                "threshold_std": 2.0,  # 2 standard deviations
                "severity": "medium"
            },
            "improvement": {
                "threshold_change": 0.15,  # 15% improvement
                "min_data_points": 5,
                "severity": "low"
            }
        }
    
    async def check_alerts(
        self, 
        trend_analysis: TrendAnalysis
    ) -> List[TrendAlert]:
        """Check for alert conditions in trend analysis."""
        
        alerts = []
        
        # Check for regression
        regression_alert = await self._check_regression_alert(trend_analysis)
        if regression_alert:
            alerts.append(regression_alert)
        
        # Check for high volatility
        volatility_alert = await self._check_volatility_alert(trend_analysis)
        if volatility_alert:
            alerts.append(volatility_alert)
        
        # Check for anomalies
        anomaly_alerts = await self._check_anomaly_alerts(trend_analysis)
        alerts.extend(anomaly_alerts)
        
        # Check for improvements
        improvement_alert = await self._check_improvement_alert(trend_analysis)
        if improvement_alert:
            alerts.append(improvement_alert)
        
        # Store alerts in database
        for alert in alerts:
            await self.db.store_alert(alert)
        
        return alerts
    
    async def _check_regression_alert(
        self, 
        trend_analysis: TrendAnalysis
    ) -> Optional[TrendAlert]:
        """Check for regression alert."""
        
        rules = self.alert_rules["regression"]
        
        if len(trend_analysis.data_points) < rules["min_data_points"]:
            return None
        
        # Check if trend is significantly negative
        if (trend_analysis.trend_direction == "decreasing" and 
            trend_analysis.slope < rules["threshold_change"] and
            trend_analysis.trend_strength > 0.5):
            
            alert_id = f"regression_{trend_analysis.metric_name}_{int(time.time())}"
            
            return TrendAlert(
                alert_id=alert_id,
                metric_name=trend_analysis.metric_name,
                alert_type="regression",
                severity=rules["severity"],
                triggered_at=datetime.now(timezone.utc),
                description=f"Quality regression detected in {trend_analysis.metric_name}",
                current_value=trend_analysis.data_points[-1].value,
                threshold_value=None,
                trend_data=trend_analysis,
                recommended_actions=[
                    "Investigate recent changes that may have caused regression",
                    "Review code commits in the affected timeframe",
                    "Run comprehensive tests to identify root cause",
                    "Consider rollback if regression is severe"
                ]
            )
        
        return None
    
    async def _check_volatility_alert(
        self, 
        trend_analysis: TrendAnalysis
    ) -> Optional[TrendAlert]:
        """Check for high volatility alert."""
        
        rules = self.alert_rules["volatility"]
        
        if len(trend_analysis.data_points) < rules["min_data_points"]:
            return None
        
        if trend_analysis.volatility > rules["threshold"]:
            
            alert_id = f"volatility_{trend_analysis.metric_name}_{int(time.time())}"
            
            return TrendAlert(
                alert_id=alert_id,
                metric_name=trend_analysis.metric_name,
                alert_type="volatility",
                severity=rules["severity"],
                triggered_at=datetime.now(timezone.utc),
                description=f"High volatility detected in {trend_analysis.metric_name}",
                current_value=trend_analysis.volatility,
                threshold_value=rules["threshold"],
                trend_data=trend_analysis,
                recommended_actions=[
                    "Investigate causes of metric instability",
                    "Check for environmental factors affecting measurements",
                    "Consider smoothing techniques for better trend analysis",
                    "Review measurement methodology for consistency"
                ]
            )
        
        return None
    
    async def _check_anomaly_alerts(
        self, 
        trend_analysis: TrendAnalysis
    ) -> List[TrendAlert]:
        """Check for anomaly alerts."""
        
        alerts = []
        rules = self.alert_rules["anomaly"]
        
        for anomaly in trend_analysis.anomalies:
            alert_id = f"anomaly_{trend_analysis.metric_name}_{int(anomaly.timestamp.timestamp())}"
            
            alert = TrendAlert(
                alert_id=alert_id,
                metric_name=trend_analysis.metric_name,
                alert_type="anomaly",
                severity=rules["severity"],
                triggered_at=anomaly.timestamp,
                description=f"Anomalous value detected in {trend_analysis.metric_name}",
                current_value=anomaly.value,
                threshold_value=None,
                trend_data=trend_analysis,
                recommended_actions=[
                    "Investigate the specific event that caused the anomaly",
                    "Check system logs around the anomaly timestamp",
                    "Verify data collection accuracy",
                    "Consider if anomaly represents a legitimate spike or error"
                ]
            )
            alerts.append(alert)
        
        return alerts
    
    async def _check_improvement_alert(
        self, 
        trend_analysis: TrendAnalysis
    ) -> Optional[TrendAlert]:
        """Check for significant improvement alert."""
        
        rules = self.alert_rules["improvement"]
        
        if len(trend_analysis.data_points) < rules["min_data_points"]:
            return None
        
        # Check if trend is significantly positive
        if (trend_analysis.trend_direction == "increasing" and 
            trend_analysis.slope > rules["threshold_change"] and
            trend_analysis.trend_strength > 0.6):
            
            alert_id = f"improvement_{trend_analysis.metric_name}_{int(time.time())}"
            
            return TrendAlert(
                alert_id=alert_id,
                metric_name=trend_analysis.metric_name,
                alert_type="improvement",
                severity=rules["severity"],
                triggered_at=datetime.now(timezone.utc),
                description=f"Significant improvement detected in {trend_analysis.metric_name}",
                current_value=trend_analysis.data_points[-1].value,
                threshold_value=None,
                trend_data=trend_analysis,
                recommended_actions=[
                    "Document the changes that led to improvement",
                    "Share best practices with other teams",
                    "Monitor to ensure improvement is sustained",
                    "Consider applying similar changes to other metrics"
                ]
            )
        
        return None


class TrendTracker:
    """Main trend tracking and analysis system."""
    
    def __init__(self, db_path: Path = None):
        self.logger = AstolfoLogger(__name__)
        self.db = TrendDatabase(db_path)
        self.analyzer = TrendAnalyzer()
        self.alert_manager = TrendAlertManager(self.db)
        
        # Metrics to track
        self.tracked_metrics = [
            "overall_quality_score",
            "code_coverage_percentage",
            "test_coverage_percentage", 
            "security_score",
            "performance_score",
            "reliability_score",
            "critical_issues_count",
            "build_success_rate",
            "deployment_frequency",
            "mean_time_to_recovery"
        ]
    
    async def record_metric(
        self, 
        metric_name: str, 
        value: float, 
        timestamp: datetime = None,
        source: str = "unknown",
        category: str = "general",
        metadata: Dict[str, Any] = None
    ) -> None:
        """Record a single metric value."""
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        if metadata is None:
            metadata = {}
        
        # Add metric name to metadata
        metadata["metric_name"] = metric_name
        
        data_point = TrendDataPoint(
            timestamp=timestamp,
            value=value,
            metadata=metadata,
            source=source,
            category=category
        )
        
        await self.db.store_data_point(data_point)
        self.logger.debug(f"Recorded metric {metric_name}: {value}")
    
    async def record_quality_report(self, quality_report: Dict[str, Any]) -> None:
        """Record metrics from a quality report."""
        
        timestamp = datetime.now(timezone.utc)
        
        # Extract key metrics from quality report
        metrics_to_record = {
            "overall_quality_score": quality_report.get("summary", {}).get("overall_quality_score", 0),
            "total_issues": quality_report.get("summary", {}).get("total_issues", 0),
            "critical_issues": quality_report.get("summary", {}).get("critical_issues", 0),
            "compliance_percentage": quality_report.get("summary", {}).get("compliance_percentage", 0)
        }
        
        # Record component scores
        component_analysis = quality_report.get("component_analysis", {})
        for component_name, component_data in component_analysis.items():
            metric_name = f"{component_name}_score"
            metrics_to_record[metric_name] = component_data.get("score", 0)
        
        # Record all metrics
        data_points = []
        for metric_name, value in metrics_to_record.items():
            data_point = TrendDataPoint(
                timestamp=timestamp,
                value=value,
                metadata={
                    "metric_name": metric_name,
                    "report_id": quality_report.get("report_metadata", {}).get("report_id", "unknown")
                },
                source="quality_report",
                category="quality"
            )
            data_points.append(data_point)
        
        await self.db.store_data_points(data_points)
        self.logger.info(f"Recorded {len(data_points)} metrics from quality report")
    
    async def analyze_metric_trend(
        self, 
        metric_name: str,
        days_back: int = 30
    ) -> TrendAnalysis:
        """Analyze trend for a specific metric."""
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        
        data_points = await self.db.get_trend_data(metric_name, start_time, end_time)
        
        trend_analysis = await self.analyzer.analyze_trend(data_points, metric_name)
        
        # Check for alerts
        alerts = await self.alert_manager.check_alerts(trend_analysis)
        if alerts:
            self.logger.info(f"Generated {len(alerts)} alerts for {metric_name}")
        
        return trend_analysis
    
    async def analyze_all_trends(self, days_back: int = 30) -> Dict[str, TrendAnalysis]:
        """Analyze trends for all tracked metrics."""
        
        trend_analyses = {}
        
        for metric_name in self.tracked_metrics:
            try:
                trend_analysis = await self.analyze_metric_trend(metric_name, days_back)
                trend_analyses[metric_name] = trend_analysis
            except Exception as e:
                self.logger.warning(f"Failed to analyze trend for {metric_name}: {e}")
        
        return trend_analyses
    
    async def generate_trend_report(
        self, 
        days_back: int = 30,
        include_predictions: bool = True,
        include_comparisons: bool = True
    ) -> TrendReport:
        """Generate comprehensive trend report."""
        
        report_id = f"TREND_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        generated_at = datetime.now(timezone.utc)
        end_time = generated_at
        start_time = end_time - timedelta(days=days_back)
        
        # Analyze all trends
        trend_analyses = await self.analyze_all_trends(days_back)
        
        # Generate comparisons
        trend_comparisons = []
        if include_comparisons and len(trend_analyses) > 1:
            trend_comparisons = await self.analyzer.compare_trends(trend_analyses)
        
        # Get active alerts
        alert_data = await self.db.get_active_alerts()
        active_alerts = []
        for alert_dict in alert_data:
            # Reconstruct TrendAlert objects (simplified)
            alert = TrendAlert(
                alert_id=alert_dict["alert_id"],
                metric_name=alert_dict["metric_name"],
                alert_type=alert_dict["alert_type"],
                severity=alert_dict["severity"],
                triggered_at=alert_dict["triggered_at"],
                description=alert_dict["description"],
                current_value=alert_dict["current_value"],
                threshold_value=alert_dict["threshold_value"],
                trend_data=None,  # Would need to reconstruct
                recommended_actions=[]
            )
            active_alerts.append(alert)
        
        # Generate summary
        summary = await self._generate_trend_summary(trend_analyses, active_alerts)
        
        # Generate predictions
        predictions = {}
        if include_predictions:
            for metric_name, trend_analysis in trend_analyses.items():
                predictions[metric_name] = trend_analysis.forecast
        
        # Generate recommendations
        recommendations = await self._generate_trend_recommendations(trend_analyses, active_alerts)
        
        return TrendReport(
            report_id=report_id,
            generated_at=generated_at,
            time_period=(start_time, end_time),
            analyzed_metrics=list(trend_analyses.keys()),
            trend_analyses=trend_analyses,
            trend_comparisons=trend_comparisons,
            active_alerts=active_alerts,
            summary=summary,
            predictions=predictions,
            recommendations=recommendations
        )
    
    async def _generate_trend_summary(
        self, 
        trend_analyses: Dict[str, TrendAnalysis],
        active_alerts: List[TrendAlert]
    ) -> Dict[str, Any]:
        """Generate summary of trend analysis."""
        
        summary = {
            "total_metrics_analyzed": len(trend_analyses),
            "active_alerts": len(active_alerts),
            "metrics_improving": 0,
            "metrics_declining": 0,
            "metrics_stable": 0,
            "highest_volatility_metric": None,
            "strongest_trend_metric": None,
            "alert_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0}
        }
        
        # Analyze trend directions
        for metric_name, trend_analysis in trend_analyses.items():
            if trend_analysis.trend_direction == "increasing":
                summary["metrics_improving"] += 1
            elif trend_analysis.trend_direction == "decreasing":
                summary["metrics_declining"] += 1
            else:
                summary["metrics_stable"] += 1
        
        # Find highest volatility metric
        if trend_analyses:
            highest_volatility_metric = max(
                trend_analyses.keys(),
                key=lambda name: trend_analyses[name].volatility
            )
            summary["highest_volatility_metric"] = highest_volatility_metric
            
            # Find strongest trend metric
            strongest_trend_metric = max(
                trend_analyses.keys(),
                key=lambda name: trend_analyses[name].trend_strength
            )
            summary["strongest_trend_metric"] = strongest_trend_metric
        
        # Alert breakdown
        for alert in active_alerts:
            if alert.severity in summary["alert_breakdown"]:
                summary["alert_breakdown"][alert.severity] += 1
        
        return summary
    
    async def _generate_trend_recommendations(
        self, 
        trend_analyses: Dict[str, TrendAnalysis],
        active_alerts: List[TrendAlert]
    ) -> List[str]:
        """Generate recommendations based on trend analysis."""
        
        recommendations = []
        
        # Recommendations based on declining trends
        declining_metrics = [
            name for name, trend in trend_analyses.items()
            if trend.trend_direction == "decreasing" and trend.trend_strength > 0.5
        ]
        
        if declining_metrics:
            recommendations.append(
                f"Address declining trends in: {', '.join(declining_metrics[:3])}"
            )
        
        # Recommendations based on high volatility
        volatile_metrics = [
            name for name, trend in trend_analyses.items()
            if trend.volatility > 0.3
        ]
        
        if volatile_metrics:
            recommendations.append(
                f"Investigate volatility in: {', '.join(volatile_metrics[:3])}"
            )
        
        # Recommendations based on critical alerts
        critical_alerts = [alert for alert in active_alerts if alert.severity == "critical"]
        if critical_alerts:
            recommendations.append(
                f"URGENT: Address {len(critical_alerts)} critical trend alerts"
            )
        
        # Recommendations based on successful trends
        improving_metrics = [
            name for name, trend in trend_analyses.items()
            if trend.trend_direction == "increasing" and trend.trend_strength > 0.6
        ]
        
        if improving_metrics:
            recommendations.append(
                f"Document and replicate success patterns from: {', '.join(improving_metrics[:2])}"
            )
        
        # General recommendations
        if len(trend_analyses) < 5:
            recommendations.append("Consider tracking additional quality metrics for better insights")
        
        return recommendations
    
    async def export_trend_data(
        self, 
        metric_name: str,
        format_type: str = "csv",
        days_back: int = 30
    ) -> Path:
        """Export trend data to file."""
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        
        data_points = await self.db.get_trend_data(metric_name, start_time, end_time)
        
        output_dir = Path("trend_exports")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{metric_name}_trend_{timestamp}.{format_type}"
        
        if format_type == "csv":
            await self._export_csv(data_points, output_file)
        elif format_type == "json":
            await self._export_json(data_points, output_file)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
        
        self.logger.info(f"Exported trend data to: {output_file}")
        return output_file
    
    async def _export_csv(self, data_points: List[TrendDataPoint], output_file: Path) -> None:
        """Export data points to CSV."""
        import csv
        
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['timestamp', 'value', 'source', 'category'])
            
            # Write data
            for dp in data_points:
                writer.writerow([
                    dp.timestamp.isoformat(),
                    dp.value,
                    dp.source,
                    dp.category
                ])
    
    async def _export_json(self, data_points: List[TrendDataPoint], output_file: Path) -> None:
        """Export data points to JSON."""
        data = []
        for dp in data_points:
            data.append({
                'timestamp': dp.timestamp.isoformat(),
                'value': dp.value,
                'source': dp.source,
                'category': dp.category,
                'metadata': dp.metadata
            })
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)


def run_trend_tracker_example():
    """Example usage of TrendTracker."""
    import asyncio
    
    async def example():
        # Initialize trend tracker
        tracker = TrendTracker()
        
        # Record some sample metrics
        now = datetime.now(timezone.utc)
        for i in range(10):
            timestamp = now - timedelta(days=i)
            
            # Simulate improving quality score
            quality_score = 75 + (i * 2) + (i * 0.1)  # Slight upward trend
            await tracker.record_metric(
                "overall_quality_score",
                quality_score,
                timestamp,
                source="quality_report",
                category="quality"
            )
            
            # Simulate decreasing issue count
            issues = 20 - i + (i % 3)  # Downward trend with some volatility
            await tracker.record_metric(
                "critical_issues_count", 
                issues,
                timestamp,
                source="issue_tracker",
                category="quality"
            )
        
        # Analyze trends
        quality_trend = await tracker.analyze_metric_trend("overall_quality_score", days_back=15)
        issues_trend = await tracker.analyze_metric_trend("critical_issues_count", days_back=15)
        
        print(f"Quality Score Trend: {quality_trend.trend_direction} (strength: {quality_trend.trend_strength:.2f})")
        print(f"Critical Issues Trend: {issues_trend.trend_direction} (strength: {issues_trend.trend_strength:.2f})")
        print(f"Quality Score Forecast: {quality_trend.forecast}")
        
        # Generate comprehensive report
        report = await tracker.generate_trend_report(days_back=15)
        
        print(f"\nTrend Report: {report.report_id}")
        print(f"Metrics Analyzed: {report.summary['total_metrics_analyzed']}")
        print(f"Active Alerts: {report.summary['active_alerts']}")
        print(f"Improving Metrics: {report.summary['metrics_improving']}")
        print(f"Declining Metrics: {report.summary['metrics_declining']}")
        
        if report.recommendations:
            print("\nRecommendations:")
            for rec in report.recommendations:
                print(f"- {rec}")
    
    asyncio.run(example())


if __name__ == "__main__":
    run_trend_tracker_example()