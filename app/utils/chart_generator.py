"""
Utility for generating chart data from document content.
"""
import json
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

def generate_chart_data(data_type: str, title: str, labels: List[str], 
                        datasets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate chart data in a format suitable for frontend charting libraries.
    
    Args:
        data_type: Type of chart (bar, line, pie, etc.)
        title: Chart title
        labels: X-axis labels or category names
        datasets: List of datasets with values and styling
        
    Returns:
        Dictionary with chart configuration
    """
    try:
        chart_data = {
            "type": data_type,
            "title": title,
            "data": {
                "labels": labels,
                "datasets": datasets
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False
            }
        }
        
        return chart_data
    except Exception as e:
        logger.error(f"Error generating chart data: {str(e)}")
        return {
            "error": str(e),
            "type": "error"
        }

def extract_financial_data_for_chart(document_content: str) -> Optional[Dict[str, Any]]:
    """
    Extract financial data from document content and format it for charts.
    
    Args:
        document_content: The content of the document
        
    Returns:
        Dictionary with chart data or None if extraction fails
    """
    try:
        # Initialize data containers
        quarters = ["Q1", "Q2", "Q3", "Q4"]
        revenue_data = []
        expense_data = []
        profit_data = []
        
        # Simple parsing logic for financial data
        lines = document_content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Extract revenue data
            if any(f"{q} Revenue: $" in line for q in quarters):
                for i, quarter in enumerate(quarters):
                    if f"{quarter} Revenue: $" in line:
                        try:
                            value = int(line.split('$')[1].replace(',', ''))
                            revenue_data.append(value)
                        except (IndexError, ValueError):
                            pass
            
            # Extract expense data
            if any(f"{q} Expenses: $" in line for q in quarters):
                for i, quarter in enumerate(quarters):
                    if f"{quarter} Expenses: $" in line:
                        try:
                            value = int(line.split('$')[1].replace(',', ''))
                            expense_data.append(value)
                        except (IndexError, ValueError):
                            pass
            
            # Extract profit data
            if any(f"{q} Profit: $" in line for q in quarters):
                for i, quarter in enumerate(quarters):
                    if f"{quarter} Profit: $" in line:
                        try:
                            value = int(line.split('$')[1].replace(',', ''))
                            profit_data.append(value)
                        except (IndexError, ValueError):
                            pass
        
        # Check if we have enough data
        if len(revenue_data) == 4 and len(expense_data) == 4 and len(profit_data) == 4:
            # Create chart data
            chart_data = generate_chart_data(
                data_type="bar",
                title="Quarterly Financial Performance",
                labels=quarters,
                datasets=[
                    {
                        "label": "Revenue",
                        "data": revenue_data,
                        "backgroundColor": "rgba(54, 162, 235, 0.5)",
                        "borderColor": "rgba(54, 162, 235, 1)",
                        "borderWidth": 1
                    },
                    {
                        "label": "Expenses",
                        "data": expense_data,
                        "backgroundColor": "rgba(255, 99, 132, 0.5)",
                        "borderColor": "rgba(255, 99, 132, 1)",
                        "borderWidth": 1
                    },
                    {
                        "label": "Profit",
                        "data": profit_data,
                        "backgroundColor": "rgba(75, 192, 192, 0.5)",
                        "borderColor": "rgba(75, 192, 192, 1)",
                        "borderWidth": 1
                    }
                ]
            )
            
            return chart_data
        
        # If we don't have complete quarterly data, try to create a simple chart
        # with whatever data we have
        available_data = []
        if revenue_data:
            available_data.append({
                "label": "Revenue",
                "data": revenue_data,
                "backgroundColor": "rgba(54, 162, 235, 0.5)"
            })
        if expense_data:
            available_data.append({
                "label": "Expenses",
                "data": expense_data,
                "backgroundColor": "rgba(255, 99, 132, 0.5)"
            })
        if profit_data:
            available_data.append({
                "label": "Profit",
                "data": profit_data,
                "backgroundColor": "rgba(75, 192, 192, 0.5)"
            })
        
        if available_data:
            # Use available quarters based on data length
            available_quarters = quarters[:len(available_data[0]["data"])]
            
            chart_data = generate_chart_data(
                data_type="bar",
                title="Financial Performance",
                labels=available_quarters,
                datasets=available_data
            )
            
            return chart_data
        
        return None
    
    except Exception as e:
        logger.error(f"Error extracting financial data for chart: {str(e)}")
        return None

def generate_trend_chart(title: str, labels: List[str], data: List[int], 
                         color: str = "rgba(75, 192, 192, 0.5)") -> Dict[str, Any]:
    """
    Generate a trend chart (line chart) for a single dataset.
    
    Args:
        title: Chart title
        labels: X-axis labels
        data: Y-axis values
        color: Line color
        
    Returns:
        Dictionary with chart configuration
    """
    try:
        chart_data = generate_chart_data(
            data_type="line",
            title=title,
            labels=labels,
            datasets=[
                {
                    "label": title,
                    "data": data,
                    "backgroundColor": color,
                    "borderColor": color.replace("0.5", "1"),
                    "borderWidth": 2,
                    "tension": 0.1
                }
            ]
        )
        
        return chart_data
    except Exception as e:
        logger.error(f"Error generating trend chart: {str(e)}")
        return {
            "error": str(e),
            "type": "error"
        }

def generate_comparison_chart(title: str, labels: List[str], 
                              datasets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a comparison chart (bar chart) for multiple datasets.
    
    Args:
        title: Chart title
        labels: X-axis labels
        datasets: List of datasets with values and styling
        
    Returns:
        Dictionary with chart configuration
    """
    try:
        chart_data = generate_chart_data(
            data_type="bar",
            title=title,
            labels=labels,
            datasets=datasets
        )
        
        return chart_data
    except Exception as e:
        logger.error(f"Error generating comparison chart: {str(e)}")
        return {
            "error": str(e),
            "type": "error"
        }
