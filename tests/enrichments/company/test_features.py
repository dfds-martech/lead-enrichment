"""Tests for company feature extraction and assessment logic."""

import pytest
from enrichments.company.features import _assess_financial_health
from enrichments.company.schemas import CompanyFinancials


class TestFinancialHealthAssessment:
    """Test financial health assessment logic."""
    
    def test_healthy_with_credit_risk_a(self):
        """Company with Orbis A rating should be healthy."""
        fin = CompanyFinancials(
            credit_risk_rating_label="A"
        )
        assert _assess_financial_health(fin) == "healthy"
    
    def test_moderate_with_credit_risk_b(self):
        """Company with Orbis B rating should be moderate."""
        fin = CompanyFinancials(
            credit_risk_rating_label="B+"
        )
        assert _assess_financial_health(fin) == "moderate"
    
    def test_at_risk_with_credit_risk_c(self):
        """Company with Orbis C rating should be at_risk."""
        fin = CompanyFinancials(
            credit_risk_rating_label="C"
        )
        assert _assess_financial_health(fin) == "at_risk"
    
    def test_healthy_positive_both(self):
        """Company with positive profit and cash flow should be healthy."""
        fin = CompanyFinancials(
            profit_before_tax=100000,
            cash_flow=50000
        )
        assert _assess_financial_health(fin) == "healthy"
    
    def test_at_risk_negative_both(self):
        """Company with negative profit and cash flow should be at_risk."""
        fin = CompanyFinancials(
            profit_before_tax=-50000,
            cash_flow=-20000
        )
        assert _assess_financial_health(fin) == "at_risk"
    
    def test_moderate_mixed_signals(self):
        """Company with positive profit but negative cash flow should be moderate."""
        fin = CompanyFinancials(
            profit_before_tax=100000,
            cash_flow=-20000
        )
        assert _assess_financial_health(fin) == "moderate"
    
    def test_moderate_zero_values(self):
        """Zero profit and zero cash flow should be moderate (break-even)."""
        fin = CompanyFinancials(
            profit_before_tax=0,
            cash_flow=0
        )
        assert _assess_financial_health(fin) == "moderate"
    
    def test_unknown_no_financials(self):
        """No financials object should return unknown."""
        assert _assess_financial_health(None) == "unknown"
    
    def test_unknown_no_data(self):
        """No profit or cash flow data should return unknown."""
        fin = CompanyFinancials(
            revenue=1000000,
            total_assets=500000
        )
        assert _assess_financial_health(fin) == "unknown"
    
    def test_moderate_positive_profit_only(self):
        """Positive profit with no cash flow data should be moderate."""
        fin = CompanyFinancials(
            profit_before_tax=100000
        )
        assert _assess_financial_health(fin) == "moderate"
    
    def test_at_risk_negative_profit_only(self):
        """Negative profit with no cash flow data should be at_risk."""
        fin = CompanyFinancials(
            profit_before_tax=-50000
        )
        assert _assess_financial_health(fin) == "at_risk"
    
    def test_moderate_positive_cashflow_only(self):
        """Positive cash flow with no profit data should be moderate."""
        fin = CompanyFinancials(
            cash_flow=50000
        )
        assert _assess_financial_health(fin) == "moderate"
    
    def test_at_risk_negative_cashflow_only(self):
        """Negative cash flow with no profit data should be at_risk."""
        fin = CompanyFinancials(
            cash_flow=-20000
        )
        assert _assess_financial_health(fin) == "at_risk"
