"""
Auto-D Kenya - Engines Module
All calculation engines for the platform
"""

from .fuel_service import (
    FuelService,
    get_fuel_price,
    calculate_energy_cost,
    FUEL_TYPES
)

from .depreciation_engine import (
    DepreciationEngine,
    calculate_depreciation,
    DEPRECIATION_RATES
)

from .insurance_engine import (
    InsuranceEngine,
    estimate_insurance,
    INSURANCE_RATES
)

from .tyre_engine import (
    TyreEngine,
    calculate_tyre_cost,
    TYRE_DATA
)

from .maintenance_engine import (
    MaintenanceEngine,
    calculate_service_cost,
    SERVICE_COSTS
)

from .finance_engine import (
    FinanceEngine,
    calculate_loan_amortization,
    calculate_interest
)

from .battery_engine import (
    BatteryEngine,
    calculate_battery_reserve
)

from .environmental_engine import (
    EnvironmentalEngine,
    calculate_co2_emissions
)

from .market_intelligence_engine import (
    MarketIntelligenceEngine,
    get_market_data
)

from .running_cost_engine import (
    RunningCostEngine,
    RunningCostResult
)

from .valuation_engine import (
    ValuationEngine,
    calculate_vehicle_value,
    ValuationResult
)

from .ownership_engine import (
    OwnershipEngine,
    calculate_ownership_cost,
    OwnershipResult
)

from .report_engine import (
    ReportEngine,
    generate_report
)

__all__ = [
    'FuelService',
    'get_fuel_price',
    'calculate_energy_cost',
    'FUEL_TYPES',
    'DepreciationEngine',
    'calculate_depreciation',
    'DEPRECIATION_RATES',
    'InsuranceEngine',
    'estimate_insurance',
    'INSURANCE_RATES',
    'TyreEngine',
    'calculate_tyre_cost',
    'TYRE_DATA',
    'MaintenanceEngine',
    'calculate_service_cost',
    'SERVICE_COSTS',
    'FinanceEngine',
    'calculate_loan_amortization',
    'calculate_interest',
    'BatteryEngine',
    'calculate_battery_reserve',
    'EnvironmentalEngine',
    'calculate_co2_emissions',
    'MarketIntelligenceEngine',
    'get_market_data',
    'RunningCostEngine',
    'RunningCostResult',
    'ValuationEngine',
    'calculate_vehicle_value',
    'ValuationResult',
    'OwnershipEngine',
    'calculate_ownership_cost',
    'OwnershipResult',
    'ReportEngine',
    'generate_report'
]
