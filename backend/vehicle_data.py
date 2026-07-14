# vehicle_data.py - Complete Vehicle Database for Kenya
# Includes: Cars, SUVs, Pickups, Commercial, Industrial, Farm Machinery, Bikes, Tuktuks, Generators

VEHICLE_DATABASE = {
    # ============================================
    # 1. PASSENGER VEHICLES - CARS & SUVs
    # ============================================
    "toyota": {
        "category": "passenger",
        "models": {
            "prado": {
                "price": 5200000,
                "fuel_efficiency": 11,
                "service_interval": 10000,
                "minor_service": 18000,
                "major_service": 65000,
                "tyre_size": "265/65R17",
                "tyre_cost": 32000,
                "maintenance_per_km": 14,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.045,
                "engine_options": ["2.8 Diesel", "3.0 Diesel", "4.0 Petrol"],
                "transmission_options": ["Automatic", "Manual"],
                "fuel_types": ["Diesel", "Petrol"]
            },
            "hilux": {
                "price": 3800000,
                "fuel_efficiency": 12,
                "service_interval": 10000,
                "minor_service": 15000,
                "major_service": 55000,
                "tyre_size": "265/70R16",
                "tyre_cost": 28000,
                "maintenance_per_km": 12,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.045,
                "engine_options": ["2.4 Diesel", "2.8 Diesel", "4.0 Petrol"],
                "transmission_options": ["Automatic", "Manual"],
                "fuel_types": ["Diesel", "Petrol"]
            },
            "fortuner": {
                "price": 4500000,
                "fuel_efficiency": 10,
                "service_interval": 10000,
                "minor_service": 16000,
                "major_service": 58000,
                "tyre_size": "265/60R18",
                "tyre_cost": 35000,
                "maintenance_per_km": 13,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.045,
                "engine_options": ["2.4 Diesel", "2.8 Diesel"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Diesel"]
            },
            "land_cruiser": {
                "price": 12000000,
                "fuel_efficiency": 8,
                "service_interval": 10000,
                "minor_service": 25000,
                "major_service": 90000,
                "tyre_size": "285/60R18",
                "tyre_cost": 45000,
                "maintenance_per_km": 18,
                "depreciation_rate": 0.18,
                "depreciation_subsequent": 0.10,
                "insurance_rate": 0.045,
                "engine_options": ["4.5 Diesel", "4.6 Petrol", "5.7 Petrol"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Diesel", "Petrol"]
            },
            "corolla": {
                "price": 2000000,
                "fuel_efficiency": 15,
                "service_interval": 15000,
                "minor_service": 10000,
                "major_service": 35000,
                "tyre_size": "195/65R15",
                "tyre_cost": 18000,
                "maintenance_per_km": 6,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.040,
                "engine_options": ["1.5 Petrol", "1.8 Petrol", "2.0 Diesel"],
                "transmission_options": ["Manual", "Automatic", "CVT"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "rav4": {
                "price": 3500000,
                "fuel_efficiency": 13,
                "service_interval": 15000,
                "minor_service": 12000,
                "major_service": 40000,
                "tyre_size": "225/65R17",
                "tyre_cost": 25000,
                "maintenance_per_km": 8,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.042,
                "engine_options": ["2.0 Petrol", "2.5 Hybrid"],
                "transmission_options": ["CVT", "Automatic"],
                "fuel_types": ["Petrol", "Hybrid"]
            },
            "camry": {
                "price": 4000000,
                "fuel_efficiency": 14,
                "service_interval": 15000,
                "minor_service": 13000,
                "major_service": 42000,
                "tyre_size": "215/55R17",
                "tyre_cost": 22000,
                "maintenance_per_km": 7,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.042,
                "engine_options": ["2.5 Petrol", "3.5 Petrol", "2.5 Hybrid"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Petrol", "Hybrid"]
            },
            "hiace": {
                "price": 4500000,
                "fuel_efficiency": 9,
                "service_interval": 10000,
                "minor_service": 20000,
                "major_service": 70000,
                "tyre_size": "195/70R15",
                "tyre_cost": 25000,
                "maintenance_per_km": 16,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.050,
                "engine_options": ["2.5 Diesel", "3.0 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            },
            "sienta": {
                "price": 2800000,
                "fuel_efficiency": 12,
                "service_interval": 10000,
                "minor_service": 14000,
                "major_service": 48000,
                "tyre_size": "185/60R15",
                "tyre_cost": 20000,
                "maintenance_per_km": 10,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.044,
                "engine_options": ["1.5 Petrol", "1.8 Petrol"],
                "transmission_options": ["CVT"],
                "fuel_types": ["Petrol"]
            }
        }
    },
    
    "nissan": {
        "category": "passenger",
        "models": {
            "xtrail": {
                "price": 3200000,
                "fuel_efficiency": 12,
                "service_interval": 15000,
                "minor_service": 12000,
                "major_service": 42000,
                "tyre_size": "225/60R17",
                "tyre_cost": 24000,
                "maintenance_per_km": 8,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.042,
                "engine_options": ["2.0 Petrol", "2.5 Petrol"],
                "transmission_options": ["CVT", "Automatic"],
                "fuel_types": ["Petrol"]
            },
            "patrol": {
                "price": 8000000,
                "fuel_efficiency": 7,
                "service_interval": 10000,
                "minor_service": 20000,
                "major_service": 75000,
                "tyre_size": "265/70R18",
                "tyre_cost": 40000,
                "maintenance_per_km": 15,
                "depreciation_rate": 0.18,
                "depreciation_subsequent": 0.10,
                "insurance_rate": 0.045,
                "engine_options": ["3.0 Diesel", "4.0 Petrol"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Diesel", "Petrol"]
            },
            "note": {
                "price": 1500000,
                "fuel_efficiency": 18,
                "service_interval": 15000,
                "minor_service": 8000,
                "major_service": 28000,
                "tyre_size": "185/65R15",
                "tyre_cost": 16000,
                "maintenance_per_km": 5,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.040,
                "engine_options": ["1.2 Petrol", "1.5 Petrol"],
                "transmission_options": ["Manual", "CVT"],
                "fuel_types": ["Petrol"]
            },
            "pickup": {
                "price": 3500000,
                "fuel_efficiency": 11,
                "service_interval": 10000,
                "minor_service": 16000,
                "major_service": 58000,
                "tyre_size": "265/70R16",
                "tyre_cost": 28000,
                "maintenance_per_km": 12,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.045,
                "engine_options": ["2.5 Diesel", "3.0 Diesel"],
                "transmission_options": ["Manual", "Automatic"],
                "fuel_types": ["Diesel"]
            }
        }
    },
    
    "isuzu": {
        "category": "commercial",
        "models": {
            "dmax": {
                "price": 4000000,
                "fuel_efficiency": 12,
                "service_interval": 10000,
                "minor_service": 16000,
                "major_service": 60000,
                "tyre_size": "245/70R16",
                "tyre_cost": 28000,
                "maintenance_per_km": 12,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.045,
                "engine_options": ["1.9 Diesel", "3.0 Diesel"],
                "transmission_options": ["Manual", "Automatic"],
                "fuel_types": ["Diesel"]
            },
            "fvr": {
                "price": 8500000,
                "fuel_efficiency": 5,
                "service_interval": 8000,
                "minor_service": 35000,
                "major_service": 120000,
                "tyre_size": "11R22.5",
                "tyre_cost": 60000,
                "maintenance_per_km": 25,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.055,
                "engine_options": ["6HK1 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            },
            "npr": {
                "price": 5500000,
                "fuel_efficiency": 6,
                "service_interval": 8000,
                "minor_service": 25000,
                "major_service": 90000,
                "tyre_size": "7.50R16",
                "tyre_cost": 40000,
                "maintenance_per_km": 20,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.050,
                "engine_options": ["4.8 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            }
        }
    },
    
    "mitsubishi": {
        "category": "passenger",
        "models": {
            "pajero": {
                "price": 4800000,
                "fuel_efficiency": 10,
                "service_interval": 10000,
                "minor_service": 17000,
                "major_service": 62000,
                "tyre_size": "265/65R17",
                "tyre_cost": 32000,
                "maintenance_per_km": 14,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.045,
                "engine_options": ["2.8 Diesel", "3.2 Diesel", "3.5 Petrol"],
                "transmission_options": ["Automatic", "Manual"],
                "fuel_types": ["Diesel", "Petrol"]
            },
            "outlander": {
                "price": 3000000,
                "fuel_efficiency": 12,
                "service_interval": 15000,
                "minor_service": 11000,
                "major_service": 38000,
                "tyre_size": "225/55R18",
                "tyre_cost": 24000,
                "maintenance_per_km": 8,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.042,
                "engine_options": ["2.0 Petrol", "2.4 Petrol"],
                "transmission_options": ["CVT"],
                "fuel_types": ["Petrol"]
            },
            "l300": {
                "price": 2200000,
                "fuel_efficiency": 10,
                "service_interval": 8000,
                "minor_service": 15000,
                "major_service": 50000,
                "tyre_size": "195/70R15",
                "tyre_cost": 20000,
                "maintenance_per_km": 14,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.048,
                "engine_options": ["2.5 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            },
            "canter": {
                "price": 4800000,
                "fuel_efficiency": 6,
                "service_interval": 8000,
                "minor_service": 22000,
                "major_service": 80000,
                "tyre_size": "7.50R16",
                "tyre_cost": 38000,
                "maintenance_per_km": 18,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.050,
                "engine_options": ["4.0 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            }
        }
    },
    
    "subaru": {
        "category": "passenger",
        "models": {
            "forester": {
                "price": 3500000,
                "fuel_efficiency": 11,
                "service_interval": 15000,
                "minor_service": 13000,
                "major_service": 45000,
                "tyre_size": "225/55R17",
                "tyre_cost": 25000,
                "maintenance_per_km": 9,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.043,
                "engine_options": ["2.0 Petrol", "2.5 Petrol"],
                "transmission_options": ["CVT", "Manual"],
                "fuel_types": ["Petrol"]
            },
            "outback": {
                "price": 4200000,
                "fuel_efficiency": 10,
                "service_interval": 15000,
                "minor_service": 14000,
                "major_service": 48000,
                "tyre_size": "225/60R17",
                "tyre_cost": 26000,
                "maintenance_per_km": 10,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.043,
                "engine_options": ["2.5 Petrol", "3.6 Petrol"],
                "transmission_options": ["CVT"],
                "fuel_types": ["Petrol"]
            },
            "impreza": {
                "price": 2500000,
                "fuel_efficiency": 14,
                "service_interval": 15000,
                "minor_service": 10000,
                "major_service": 35000,
                "tyre_size": "205/50R17",
                "tyre_cost": 20000,
                "maintenance_per_km": 7,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.042,
                "engine_options": ["1.6 Petrol", "2.0 Petrol"],
                "transmission_options": ["Manual", "CVT"],
                "fuel_types": ["Petrol"]
            }
        }
    },
    
    "mercedes": {
        "category": "premium",
        "models": {
            "c_class": {
                "price": 6000000,
                "fuel_efficiency": 13,
                "service_interval": 15000,
                "minor_service": 22000,
                "major_service": 80000,
                "tyre_size": "225/45R17",
                "tyre_cost": 30000,
                "maintenance_per_km": 16,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.050,
                "engine_options": ["1.5 Petrol", "2.0 Diesel", "2.5 Petrol"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "e_class": {
                "price": 8000000,
                "fuel_efficiency": 12,
                "service_interval": 15000,
                "minor_service": 25000,
                "major_service": 90000,
                "tyre_size": "245/45R18",
                "tyre_cost": 35000,
                "maintenance_per_km": 18,
                "depreciation_rate": 0.18,
                "depreciation_subsequent": 0.10,
                "insurance_rate": 0.050,
                "engine_options": ["2.0 Diesel", "3.0 Petrol"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Diesel", "Petrol"]
            },
            "g_class": {
                "price": 25000000,
                "fuel_efficiency": 6,
                "service_interval": 10000,
                "minor_service": 40000,
                "major_service": 150000,
                "tyre_size": "265/60R18",
                "tyre_cost": 50000,
                "maintenance_per_km": 25,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.055,
                "engine_options": ["4.0 Petrol", "3.0 Diesel"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "sprinter": {
                "price": 7000000,
                "fuel_efficiency": 8,
                "service_interval": 10000,
                "minor_service": 28000,
                "major_service": 100000,
                "tyre_size": "205/70R16",
                "tyre_cost": 30000,
                "maintenance_per_km": 20,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.052,
                "engine_options": ["2.1 Diesel", "3.0 Diesel"],
                "transmission_options": ["Manual", "Automatic"],
                "fuel_types": ["Diesel"]
            }
        }
    },
    
    "bmw": {
        "category": "premium",
        "models": {
            "x3": {
                "price": 5500000,
                "fuel_efficiency": 12,
                "service_interval": 15000,
                "minor_service": 20000,
                "major_service": 75000,
                "tyre_size": "225/60R17",
                "tyre_cost": 30000,
                "maintenance_per_km": 15,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.048,
                "engine_options": ["2.0 Petrol", "2.0 Diesel"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "x5": {
                "price": 9000000,
                "fuel_efficiency": 10,
                "service_interval": 15000,
                "minor_service": 25000,
                "major_service": 90000,
                "tyre_size": "255/55R18",
                "tyre_cost": 40000,
                "maintenance_per_km": 18,
                "depreciation_rate": 0.18,
                "depreciation_subsequent": 0.10,
                "insurance_rate": 0.050,
                "engine_options": ["3.0 Petrol", "3.0 Diesel"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "3_series": {
                "price": 4800000,
                "fuel_efficiency": 14,
                "service_interval": 15000,
                "minor_service": 18000,
                "major_service": 65000,
                "tyre_size": "205/55R17",
                "tyre_cost": 25000,
                "maintenance_per_km": 13,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.045,
                "engine_options": ["2.0 Petrol", "2.0 Diesel"],
                "transmission_options": ["Automatic", "Manual"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "5_series": {
                "price": 7500000,
                "fuel_efficiency": 13,
                "service_interval": 15000,
                "minor_service": 22000,
                "major_service": 80000,
                "tyre_size": "225/55R17",
                "tyre_cost": 30000,
                "maintenance_per_km": 16,
                "depreciation_rate": 0.18,
                "depreciation_subsequent": 0.10,
                "insurance_rate": 0.048,
                "engine_options": ["2.0 Petrol", "3.0 Diesel"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Petrol", "Diesel"]
            }
        }
    },
    
    "volkswagen": {
        "category": "passenger",
        "models": {
            "golf": {
                "price": 2800000,
                "fuel_efficiency": 14,
                "service_interval": 15000,
                "minor_service": 12000,
                "major_service": 40000,
                "tyre_size": "205/55R16",
                "tyre_cost": 20000,
                "maintenance_per_km": 8,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.042,
                "engine_options": ["1.4 Petrol", "2.0 Diesel"],
                "transmission_options": ["Manual", "Automatic"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "tiguan": {
                "price": 3800000,
                "fuel_efficiency": 12,
                "service_interval": 15000,
                "minor_service": 15000,
                "major_service": 50000,
                "tyre_size": "215/65R17",
                "tyre_cost": 26000,
                "maintenance_per_km": 10,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.044,
                "engine_options": ["1.4 Petrol", "2.0 Diesel"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "polo": {
                "price": 1800000,
                "fuel_efficiency": 16,
                "service_interval": 15000,
                "minor_service": 8000,
                "major_service": 28000,
                "tyre_size": "195/55R15",
                "tyre_cost": 16000,
                "maintenance_per_km": 5,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.040,
                "engine_options": ["1.0 Petrol", "1.4 Petrol"],
                "transmission_options": ["Manual", "Automatic"],
                "fuel_types": ["Petrol"]
            },
            "crafter": {
                "price": 6000000,
                "fuel_efficiency": 7,
                "service_interval": 10000,
                "minor_service": 25000,
                "major_service": 90000,
                "tyre_size": "205/75R16",
                "tyre_cost": 30000,
                "maintenance_per_km": 18,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.052,
                "engine_options": ["2.0 Diesel"],
                "transmission_options": ["Manual", "Automatic"],
                "fuel_types": ["Diesel"]
            }
        }
    },
    
    "hyundai": {
        "category": "passenger",
        "models": {
            "tucson": {
                "price": 3200000,
                "fuel_efficiency": 13,
                "service_interval": 15000,
                "minor_service": 11000,
                "major_service": 38000,
                "tyre_size": "225/60R17",
                "tyre_cost": 24000,
                "maintenance_per_km": 8,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.042,
                "engine_options": ["2.0 Petrol", "2.2 Diesel"],
                "transmission_options": ["Automatic", "Manual"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "santa_fe": {
                "price": 4500000,
                "fuel_efficiency": 11,
                "service_interval": 15000,
                "minor_service": 14000,
                "major_service": 48000,
                "tyre_size": "235/60R18",
                "tyre_cost": 28000,
                "maintenance_per_km": 10,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.044,
                "engine_options": ["2.4 Petrol", "2.2 Diesel"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "i10": {
                "price": 1200000,
                "fuel_efficiency": 18,
                "service_interval": 15000,
                "minor_service": 6000,
                "major_service": 22000,
                "tyre_size": "175/65R14",
                "tyre_cost": 14000,
                "maintenance_per_km": 4,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.038,
                "engine_options": ["1.0 Petrol", "1.2 Petrol"],
                "transmission_options": ["Manual", "CVT"],
                "fuel_types": ["Petrol"]
            },
            "i20": {
                "price": 1500000,
                "fuel_efficiency": 17,
                "service_interval": 15000,
                "minor_service": 7000,
                "major_service": 25000,
                "tyre_size": "185/60R15",
                "tyre_cost": 16000,
                "maintenance_per_km": 5,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.040,
                "engine_options": ["1.2 Petrol", "1.4 Petrol"],
                "transmission_options": ["Manual", "CVT"],
                "fuel_types": ["Petrol"]
            }
        }
    },
    
    "ford": {
        "category": "passenger",
        "models": {
            "ranger": {
                "price": 4200000,
                "fuel_efficiency": 11,
                "service_interval": 10000,
                "minor_service": 16000,
                "major_service": 60000,
                "tyre_size": "265/70R16",
                "tyre_cost": 30000,
                "maintenance_per_km": 12,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.045,
                "engine_options": ["2.2 Diesel", "3.2 Diesel", "2.0 Diesel"],
                "transmission_options": ["Manual", "Automatic"],
                "fuel_types": ["Diesel"]
            },
            "everest": {
                "price": 5000000,
                "fuel_efficiency": 10,
                "service_interval": 10000,
                "minor_service": 18000,
                "major_service": 65000,
                "tyre_size": "265/60R18",
                "tyre_cost": 35000,
                "maintenance_per_km": 14,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.045,
                "engine_options": ["2.0 Diesel", "3.2 Diesel"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Diesel"]
            },
            "fiesta": {
                "price": 1800000,
                "fuel_efficiency": 15,
                "service_interval": 15000,
                "minor_service": 9000,
                "major_service": 32000,
                "tyre_size": "195/60R15",
                "tyre_cost": 18000,
                "maintenance_per_km": 6,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.040,
                "engine_options": ["1.0 Petrol", "1.6 Petrol"],
                "transmission_options": ["Manual", "Automatic"],
                "fuel_types": ["Petrol"]
            }
        }
    },
    
    # ============================================
    # 2. INDUSTRIAL & CONSTRUCTION MACHINERY
    # ============================================
    "industrial": {
        "category": "industrial",
        "models": {
            "excavator": {
                "price": 15000000,
                "fuel_efficiency": 4,  # litres per hour
                "service_interval": 250,  # hours
                "minor_service": 50000,
                "major_service": 200000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.025,
                "engine_options": ["4.0 Diesel", "6.0 Diesel"],
                "transmission_options": ["Hydrostatic"],
                "fuel_types": ["Diesel"]
            },
            "bulldozer": {
                "price": 25000000,
                "fuel_efficiency": 3,
                "service_interval": 200,
                "minor_service": 80000,
                "major_service": 300000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.025,
                "engine_options": ["6.0 Diesel", "8.0 Diesel"],
                "transmission_options": ["Hydrostatic"],
                "fuel_types": ["Diesel"]
            },
            "wheel_loader": {
                "price": 18000000,
                "fuel_efficiency": 5,
                "service_interval": 250,
                "minor_service": 60000,
                "major_service": 220000,
                "tyre_size": "23.5R25",
                "tyre_cost": 120000,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.025,
                "engine_options": ["5.0 Diesel", "7.0 Diesel"],
                "transmission_options": ["Hydrostatic"],
                "fuel_types": ["Diesel"]
            },
            "backhoe_loader": {
                "price": 8000000,
                "fuel_efficiency": 6,
                "service_interval": 200,
                "minor_service": 35000,
                "major_service": 150000,
                "tyre_size": "17.5R25",
                "tyre_cost": 80000,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.18,
                "depreciation_subsequent": 0.10,
                "insurance_rate": 0.030,
                "engine_options": ["3.0 Diesel", "4.0 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            },
            "motor_grader": {
                "price": 12000000,
                "fuel_efficiency": 4,
                "service_interval": 250,
                "minor_service": 45000,
                "major_service": 180000,
                "tyre_size": "17.5R25",
                "tyre_cost": 80000,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.025,
                "engine_options": ["5.0 Diesel"],
                "transmission_options": ["Hydrostatic"],
                "fuel_types": ["Diesel"]
            },
            "roller_compactor": {
                "price": 6000000,
                "fuel_efficiency": 5,
                "service_interval": 200,
                "minor_service": 25000,
                "major_service": 100000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.18,
                "depreciation_subsequent": 0.10,
                "insurance_rate": 0.028,
                "engine_options": ["2.5 Diesel", "3.0 Diesel"],
                "transmission_options": ["Hydrostatic"],
                "fuel_types": ["Diesel"]
            },
            "forklift": {
                "price": 3500000,
                "fuel_efficiency": 8,
                "service_interval": 500,
                "minor_service": 15000,
                "major_service": 60000,
                "tyre_size": "7.00-12",
                "tyre_cost": 25000,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.030,
                "engine_options": ["2.5 Diesel", "Electric"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Diesel", "Electric"]
            },
            "crane": {
                "price": 30000000,
                "fuel_efficiency": 3,
                "service_interval": 200,
                "minor_service": 100000,
                "major_service": 400000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.12,
                "depreciation_subsequent": 0.06,
                "insurance_rate": 0.020,
                "engine_options": ["8.0 Diesel", "10.0 Diesel"],
                "transmission_options": ["Hydrostatic"],
                "fuel_types": ["Diesel"]
            },
            "dump_truck": {
                "price": 20000000,
                "fuel_efficiency": 3,
                "service_interval": 250,
                "minor_service": 70000,
                "major_service": 280000,
                "tyre_size": "18.00R25",
                "tyre_cost": 150000,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.025,
                "engine_options": ["8.0 Diesel", "12.0 Diesel"],
                "transmission_options": ["Automatic"],
                "fuel_types": ["Diesel"]
            }
        }
    },
    
    # ============================================
    # 3. FARM MACHINERY
    # ============================================
    "farm": {
        "category": "farm",
        "models": {
            "tractor_100hp": {
                "price": 6000000,
                "fuel_efficiency": 8,  # litres per hour
                "service_interval": 200,
                "minor_service": 25000,
                "major_service": 100000,
                "tyre_size": "14.9R28",
                "tyre_cost": 60000,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.025,
                "engine_options": ["2.5 Diesel", "3.0 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            },
            "tractor_200hp": {
                "price": 12000000,
                "fuel_efficiency": 5,
                "service_interval": 200,
                "minor_service": 40000,
                "major_service": 150000,
                "tyre_size": "18.4R38",
                "tyre_cost": 80000,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.025,
                "engine_options": ["4.0 Diesel", "6.0 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            },
            "combine_harvester": {
                "price": 18000000,
                "fuel_efficiency": 4,
                "service_interval": 250,
                "minor_service": 60000,
                "major_service": 250000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.025,
                "engine_options": ["6.0 Diesel", "8.0 Diesel"],
                "transmission_options": ["Hydrostatic"],
                "fuel_types": ["Diesel"]
            },
            "planter": {
                "price": 3000000,
                "fuel_efficiency": 8,
                "service_interval": 300,
                "minor_service": 15000,
                "major_service": 60000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.18,
                "depreciation_subsequent": 0.10,
                "insurance_rate": 0.028,
                "engine_options": ["2.5 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            },
            "sprayer": {
                "price": 4500000,
                "fuel_efficiency": 6,
                "service_interval": 300,
                "minor_service": 20000,
                "major_service": 80000,
                "tyre_size": "420/80R46",
                "tyre_cost": 50000,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.18,
                "depreciation_subsequent": 0.10,
                "insurance_rate": 0.028,
                "engine_options": ["3.0 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            },
            "baler": {
                "price": 3500000,
                "fuel_efficiency": 7,
                "service_interval": 300,
                "minor_service": 18000,
                "major_service": 70000,
                "tyre_size": "10.0/75-15.3",
                "tyre_cost": 40000,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.18,
                "depreciation_subsequent": 0.10,
                "insurance_rate": 0.028,
                "engine_options": ["2.5 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            },
            "cultivator": {
                "price": 2000000,
                "fuel_efficiency": 10,
                "service_interval": 300,
                "minor_service": 12000,
                "major_service": 50000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.028,
                "engine_options": ["2.0 Diesel"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Diesel"]
            }
        }
    },
    
    # ============================================
    # 4. MOTORCYCLES & BIKES
    # ============================================
    "bikes": {
        "category": "bike",
        "models": {
            "boxer_bm150": {
                "price": 90000,
                "fuel_efficiency": 45,
                "service_interval": 5000,
                "minor_service": 3000,
                "major_service": 10000,
                "tyre_size": "2.75-18",
                "tyre_cost": 4000,
                "maintenance_per_km": 1.5,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.030,
                "engine_options": ["150cc Petrol"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Petrol"]
            },
            "honda_cb150": {
                "price": 150000,
                "fuel_efficiency": 50,
                "service_interval": 5000,
                "minor_service": 3500,
                "major_service": 12000,
                "tyre_size": "2.75-18",
                "tyre_cost": 5000,
                "maintenance_per_km": 1.5,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.030,
                "engine_options": ["150cc Petrol"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Petrol"]
            },
            "honda_cb250": {
                "price": 250000,
                "fuel_efficiency": 40,
                "service_interval": 5000,
                "minor_service": 5000,
                "major_service": 18000,
                "tyre_size": "3.00-18",
                "tyre_cost": 6000,
                "maintenance_per_km": 2.0,
                "depreciation_rate": 0.22,
                "depreciation_subsequent": 0.13,
                "insurance_rate": 0.032,
                "engine_options": ["250cc Petrol"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Petrol"]
            },
            "yamaha_xtz125": {
                "price": 120000,
                "fuel_efficiency": 55,
                "service_interval": 5000,
                "minor_service": 3000,
                "major_service": 10000,
                "tyre_size": "2.75-21",
                "tyre_cost": 5000,
                "maintenance_per_km": 1.5,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.030,
                "engine_options": ["125cc Petrol"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Petrol"]
            },
            "tv_apache": {
                "price": 130000,
                "fuel_efficiency": 48,
                "service_interval": 5000,
                "minor_service": 3000,
                "major_service": 11000,
                "tyre_size": "2.75-18",
                "tyre_cost": 4500,
                "maintenance_per_km": 1.5,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.030,
                "engine_options": ["160cc Petrol"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Petrol"]
            },
            "honda_africa_twin": {
                "price": 1200000,
                "fuel_efficiency": 25,
                "service_interval": 10000,
                "minor_service": 15000,
                "major_service": 50000,
                "tyre_size": "90/90-21",
                "tyre_cost": 15000,
                "maintenance_per_km": 4.0,
                "depreciation_rate": 0.20,
                "depreciation_subsequent": 0.12,
                "insurance_rate": 0.035,
                "engine_options": ["1100cc Petrol"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Petrol"]
            }
        }
    },
    
    # ============================================
    # 5. TUKTUKS / TRICYCLE
    # ============================================
    "tuktuk": {
        "category": "tuktuk",
        "models": {
            "bajaj_re": {
                "price": 300000,
                "fuel_efficiency": 35,
                "service_interval": 5000,
                "minor_service": 4000,
                "major_service": 15000,
                "tyre_size": "4.00-8",
                "tyre_cost": 4000,
                "maintenance_per_km": 2.5,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.035,
                "engine_options": ["145cc Petrol"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Petrol"]
            },
            "bajaj_compact": {
                "price": 350000,
                "fuel_efficiency": 32,
                "service_interval": 5000,
                "minor_service": 4500,
                "major_service": 16000,
                "tyre_size": "4.00-8",
                "tyre_cost": 4500,
                "maintenance_per_km": 2.8,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.035,
                "engine_options": ["175cc Petrol"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Petrol"]
            },
            "bajaj_maxima": {
                "price": 400000,
                "fuel_efficiency": 30,
                "service_interval": 5000,
                "minor_service": 5000,
                "major_service": 18000,
                "tyre_size": "4.00-8",
                "tyre_cost": 5000,
                "maintenance_per_km": 3.0,
                "depreciation_rate": 0.25,
                "depreciation_subsequent": 0.15,
                "insurance_rate": 0.035,
                "engine_options": ["200cc Petrol"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Petrol"]
            },
            "bajaj_auto_ric": {
                "price": 250000,
                "fuel_efficiency": 38,
                "service_interval": 5000,
                "minor_service": 3500,
                "major_service": 13000,
                "tyre_size": "4.00-8",
                "tyre_cost": 3500,
                "maintenance_per_km": 2.2,
                "depreciation_rate": 0.28,
                "depreciation_subsequent": 0.18,
                "insurance_rate": 0.032,
                "engine_options": ["145cc Petrol"],
                "transmission_options": ["Manual"],
                "fuel_types": ["Petrol"]
            }
        }
    },
    
    # ============================================
    # 6. GENERATORS
    # ============================================
    "generators": {
        "category": "generator",
        "models": {
            "small_5kva": {
                "price": 120000,
                "fuel_efficiency": 0.5,  # litres per hour
                "service_interval": 200,
                "minor_service": 5000,
                "major_service": 20000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.020,
                "engine_options": ["Petrol", "Diesel"],
                "transmission_options": ["N/A"],
                "fuel_types": ["Petrol", "Diesel"]
            },
            "medium_20kva": {
                "price": 400000,
                "fuel_efficiency": 0.4,
                "service_interval": 250,
                "minor_service": 10000,
                "major_service": 40000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.020,
                "engine_options": ["Diesel"],
                "transmission_options": ["N/A"],
                "fuel_types": ["Diesel"]
            },
            "large_50kva": {
                "price": 800000,
                "fuel_efficiency": 0.3,
                "service_interval": 250,
                "minor_service": 20000,
                "major_service": 80000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.15,
                "depreciation_subsequent": 0.08,
                "insurance_rate": 0.020,
                "engine_options": ["Diesel"],
                "transmission_options": ["N/A"],
                "fuel_types": ["Diesel"]
            },
            "industrial_100kva": {
                "price": 1500000,
                "fuel_efficiency": 0.25,
                "service_interval": 300,
                "minor_service": 35000,
                "major_service": 150000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.12,
                "depreciation_subsequent": 0.06,
                "insurance_rate": 0.018,
                "engine_options": ["Diesel"],
                "transmission_options": ["N/A"],
                "fuel_types": ["Diesel"]
            },
            "industrial_250kva": {
                "price": 3500000,
                "fuel_efficiency": 0.2,
                "service_interval": 300,
                "minor_service": 60000,
                "major_service": 250000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.12,
                "depreciation_subsequent": 0.06,
                "insurance_rate": 0.018,
                "engine_options": ["Diesel"],
                "transmission_options": ["N/A"],
                "fuel_types": ["Diesel"]
            },
            "solar_hybrid": {
                "price": 250000,
                "fuel_efficiency": 0,  # Solar - no fuel
                "service_interval": 500,
                "minor_service": 5000,
                "major_service": 20000,
                "tyre_size": "N/A",
                "tyre_cost": 0,
                "maintenance_per_km": 0,
                "depreciation_rate": 0.10,
                "depreciation_subsequent": 0.05,
                "insurance_rate": 0.015,
                "engine_options": ["Solar"],
                "transmission_options": ["N/A"],
                "fuel_types": ["Solar"]
            }
        }
    }
}

# ── Helper Functions ──

def get_all_makes():
    """Get all makes/brands in the database"""
    return list(VEHICLE_DATABASE.keys())

def get_category(make):
    """Get category for a make"""
    return VEHICLE_DATABASE.get(make, {}).get("category", "unknown")

def get_models_for_make(make):
    """Get all models for a specific make"""
    make_data = VEHICLE_DATABASE.get(make)
    if not make_data:
        return []
    return list(make_data.get("models", {}).keys())

def get_vehicle_data(make, model):
    """Get full vehicle data for a specific make and model"""
    make_data = VEHICLE_DATABASE.get(make)
    if not make_data:
        return None
    return make_data.get("models", {}).get(model)

def get_vehicle_price(make, model):
    """Get price for a specific vehicle"""
    data = get_vehicle_data(make, model)
    return data.get("price") if data else None

def get_fuel_efficiency(make, model):
    """Get fuel efficiency for a specific vehicle"""
    data = get_vehicle_data(make, model)
    return data.get("fuel_efficiency") if data else None

def get_service_info(make, model):
    """Get service information for a specific vehicle"""
    data = get_vehicle_data(make, model)
    if not data:
        return None
    return {
        "interval": data.get("service_interval"),
        "minor_cost": data.get("minor_service"),
        "major_cost": data.get("major_service")
    }

def get_tyre_info(make, model):
    """Get tyre information for a specific vehicle"""
    data = get_vehicle_data(make, model)
    if not data:
        return None
    return {
        "size": data.get("tyre_size"),
        "cost": data.get("tyre_cost")
    }

def get_categories():
    """Get all unique categories"""
    categories = set()
    for make, data in VEHICLE_DATABASE.items():
        categories.add(data.get("category", "unknown"))
    return sorted(categories)

def get_makes_by_category(category):
    """Get all makes in a specific category"""
    makes = []
    for make, data in VEHICLE_DATABASE.items():
        if data.get("category") == category:
            makes.append(make)
    return sorted(makes)

def search_vehicles(query):
    """Search for vehicles by make or model name"""
    results = []
    query = query.lower()
    for make, make_data in VEHICLE_DATABASE.items():
        if query in make.lower():
            for model in make_data.get("models", {}).keys():
                results.append({"make": make, "model": model})
        else:
            for model, data in make_data.get("models", {}).items():
                if query in model.lower():
                    results.append({"make": make, "model": model})
    return results
