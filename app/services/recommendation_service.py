"""
AI-Based Recommendation Engine
Generates intelligent, operational mitigation actions tailored to specific shipment risks.
"""

from typing import List, Dict, Any

class RecommendationEngine:
    @classmethod
    def generate_recommendations(
        cls,
        risk_category: str,
        overall_risk_score: float,
        weather_info: Dict[str, Any],
        anomaly_info: Dict[str, Any],
        shipment_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        recommendations = []

        # 1. Weather-Specific Recommendations
        weather_severity = weather_info.get("severity_index", 0.0)
        temp = weather_info.get("temperature_c")
        is_perishable = bool(shipment_data.get("is_perishable", False))
        mode = shipment_data.get("transport_mode", "Road")

        if weather_severity >= 0.35:
            recommendations.append({
                "type": "Weather Advisory",
                "priority": "High",
                "action": "Activate Weather Contingency Protocol",
                "description": f"Severe conditions detected in corridor ({weather_info.get('weather_description', 'Adverse weather')}, {weather_info.get('wind_speed_kmh', 0)} km/h wind). Reroute through alternate inland logistics hubs or schedule precautionary dispatch holds."
            })

        if is_perishable and temp is not None:
            if temp > 30:
                recommendations.append({
                    "type": "Cold-Chain Integrity",
                    "priority": "High",
                    "action": "Deploy Active Refrigeration Monitoring",
                    "description": f"Ambient temperature ({temp}°C) poses thermal spoilage risk. Mandate IoT temperature logger telemetry with 15-minute ping alerts."
                })
            elif temp < 0:
                recommendations.append({
                    "type": "Cold-Chain Integrity",
                    "priority": "High",
                    "action": "Install Thermal Blankets & Cargo Heaters",
                    "description": f"Sub-zero exposure ({temp}°C) threatens freezing-sensitive freight. Apply thermal foil blankets prior to tarmac staging."
                })

        # 2. Anomaly & Security Recommendations
        if anomaly_info.get("is_suspicious", False):
            for act in anomaly_info.get("recommended_actions", []):
                recommendations.append({
                    "type": "Security & Fraud Prevention",
                    "priority": "Critical",
                    "action": "Fraud Mitigation Protocol",
                    "description": act
                })

        # 3. Mode & Priority Alignments
        priority = shipment_data.get("priority", "Standard")
        stops = shipment_data.get("transit_stops", 1)

        if stops >= 3 and overall_risk_score >= 50.0:
            recommendations.append({
                "type": "Route Optimization",
                "priority": "Medium",
                "action": "Bypass Intermediate Hubs",
                "description": f"Current manifest features {stops} transit transfers. Consolidate to direct point-to-point express freight to eliminate transfer sorting delays."
            })

        carrier_delay = shipment_data.get("carrier_historical_delay_rate", 0.12)
        if carrier_delay > 0.25:
            recommendations.append({
                "type": "Carrier SLA Enforcement",
                "priority": "Medium",
                "action": "Contract Secondary Logistics Carrier",
                "description": f"Designated carrier has historical delay rate of {carrier_delay*100:.1f}%. Notify carrier operations manager of escalated SLA breach monitoring."
            })

        # 4. General Risk Level Recommendations
        if overall_risk_score >= 70.0:
            recommendations.append({
                "type": "Operational Risk",
                "priority": "High",
                "action": "Priority Expedited Escalation",
                "description": "Shipment is classified as High Risk. Transmit automated customer proactive delay advisory and assign dedicated freight coordinator."
            })
        elif overall_risk_score < 40.0 and not recommendations:
            recommendations.append({
                "type": "Standard Operations",
                "priority": "Low",
                "action": "Standard Freight Processing",
                "description": "All parameters are within normal tolerances. Maintain standard automated tracking and dispatch schedule."
            })

        return recommendations
