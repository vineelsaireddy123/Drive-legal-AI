"""
NLP Engine â€” DriveLegal.ai
Gemini-first conversational AI with rule-based offline fallback.
Domain-restricted to road safety, traffic law, and driving assistance.
"""

import re, os, json, time, requests
from collections import defaultdict
import datetime

SYSTEM_PROMPT = """You are DriveLegal.ai, a professional road safety and traffic law assistant with global coverage.

YOUR DOMAIN (answer ONLY these topics):
- Traffic laws, violations, fines, challans, and penalties across countries
- Indian traffic laws and the Motor Vehicles (Amendment) Act, 2019
- State-specific traffic rules and overrides (India)
- International traffic laws for USA, UK, UAE, Germany, Australia, Canada, and others
- Road safety education and best practices worldwide
- Emergency helpline numbers and accident procedures
- Vehicle documentation and driving license rules
- Comparative analysis of traffic laws across countries

STRICT RULES:
1. NEVER answer questions outside road safety, traffic law, or driving assistance. If a user asks about politics, programming, jokes, or general knowledge, politely decline and steer them back to traffic laws.
2. When discussing Indian violations, cite the specific Section of the Motor Vehicles Act.
3. Use the appropriate currency for each country (INR for India, USD for USA, GBP for UK, AED for UAE, EUR for Germany, AUD for Australia, CAD for Canada).
4. Be conversational, professional, and concise. Do not write essays. Use bullet points for multiple items.
5. If you do not know the exact fine, state clearly that it varies and advise checking with local authorities.
6. When calculating fines for a state (India), remember that some states have different structures than the national act.
7. When asked about a specific country, provide country-specific information including emergency numbers and local rules.

Context: You will be provided with some JSON data containing relevant rules or fine amounts to help answer the user's query. Use it accurately.
"""


class NLPEngine:
    """Gemini-first AI engine with rule-based offline fallback."""

    def __init__(self, db=None):
        self.db = db
        self.gemini_url = None
        self.api_key = None
        self.chat_sessions = {}
        self._init_gemini()
        self.fallback_patterns = self._compile_fallback_patterns()

    def _init_gemini(self):
        """Initialize the Gemini API client config."""
        self.api_key = os.environ.get('GEMINI_API_KEY', '').strip()
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY not found. NLP Engine will run in OFFLINE fallback mode only.")
            self.gemini_url = None
            return

        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        print(f"SUCCESS: Gemini REST API configured (Key prefix: {self.api_key[:5]}).")

    def _compile_fallback_patterns(self):
        """Compile regex patterns for the offline rule-based fallback engine."""
        patterns = {
            'helmet': re.compile(r'\b(helmet|without helmet|no helmet)\b', re.IGNORECASE),
            'seatbelt': re.compile(r'\b(seatbelt|seat belt|without seat belt)\b', re.IGNORECASE),
            'speeding': re.compile(r'\b(speeding|overspeeding|fast driving|speed limit)\b', re.IGNORECASE),
            'drunk': re.compile(r'\b(drunk|drinking|alcohol|dui|dwi)\b', re.IGNORECASE),
            'license': re.compile(r'\b(license|driving license|dl|without license)\b', re.IGNORECASE),
            'signal': re.compile(r'\b(red light|signal|jumping signal|stop sign)\b', re.IGNORECASE),
            'phone': re.compile(r'\b(phone|mobile|talking on phone|texting)\b', re.IGNORECASE),
            'pollution': re.compile(r'\b(puc|pollution|emissions|smog)\b', re.IGNORECASE),
            'insurance': re.compile(r'\b(insurance|without insurance|uninsured)\b', re.IGNORECASE),
            'emergency': re.compile(r'\b(emergency|ambulance|accident|sos|help|police)\b', re.IGNORECASE),
        }
        return patterns

    def _get_context(self, message):
        """Extract relevant context from the database based on the message."""
        if not self.db:
            return ""

        context_items = []
        msg_lower = message.lower()
        
        # Check against all Indian violations in the DB
        all_violations = self.db.get_all_violations()
        for key, v in all_violations.items():
            keywords = v.get('keywords', [])
            keywords.append(v.get('name', '').lower())
            
            for keyword in keywords:
                if keyword in msg_lower:
                    context_items.append(
                        f"[INDIA] Violation: {v.get('name')}\n"
                        f"Section: {v.get('section')}\n"
                        f"Fine: Rs. {v.get('fine', 'Varies')}\n"
                        f"Safety Advice: {v.get('safety_advice', 'N/A')}"
                    )
                    break
        
        # Check against global/international rules
        country_keywords = {
            'usa': ['usa', 'united states', 'america', 'american'],
            'uk': ['uk', 'united kingdom', 'britain', 'british', 'england'],
            'uae': ['uae', 'dubai', 'abu dhabi', 'emirates'],
            'germany': ['germany', 'german', 'deutschland', 'autobahn'],
            'australia': ['australia', 'australian', 'sydney', 'melbourne'],
            'canada': ['canada', 'canadian', 'toronto', 'ontario'],
        }
        
        for country_key, keywords in country_keywords.items():
            if any(kw in msg_lower for kw in keywords):
                country_data = self.db.get_country_data(country_key)
                if country_data:
                    country_name = country_data.get('name', country_key)
                    currency = country_data.get('currency_symbol', '$')
                    context_items.append(
                        f"[{country_name.upper()}] Country Info:\n"
                        f"Currency: {currency}\n"
                        f"Drive Side: {country_data.get('drive_side', 'right')}\n"
                        f"BAC Limit: {country_data.get('bac_limit', 'Varies')}\n"
                        f"Emergency: {country_data.get('emergency_number', 'N/A')}\n"
                        f"Speed Unit: {country_data.get('speed_unit', 'km/h')}"
                    )
                    # Add matching violations for the country
                    for vk, viol in country_data.get('violations', {}).items():
                        viol_name = viol.get('name', '').lower()
                        if any(word in msg_lower for word in viol_name.split() if len(word) > 3):
                            fine = viol.get('fine', {})
                            context_items.append(
                                f"[{country_name.upper()}] {viol.get('name')}:\n"
                                f"First Offense: {currency}{fine.get('first_offense', 'N/A')}\n"
                                f"Repeat: {currency}{fine.get('repeat_offense', 'N/A')}\n"
                                f"Penalties: {', '.join(viol.get('additional_penalties', []))}"
                            )
                break
        
        if not context_items:
            return ""
            
        return "DATABASE CONTEXT (Use this to answer accurately):\n" + "\n---\n".join(context_items[:5])

    def process(self, message, location=None, session_id='default', country_context=None):
        """
        Process a user message.
        Attempts Gemini first, falls back to rule-based matching if offline/failed.
        country_context: auto-detected country code (e.g. 'india', 'usa') for localised responses.
        """
        start_time = time.time()
        
        # Domain filtering - check for obvious out-of-domain prompts to save API calls
        out_of_domain = re.search(r'\b(write a poem|code|python|java|html|joke|recipe|movie|politics)\b', message, re.IGNORECASE)
        if out_of_domain:
            return {
                'text': "I am DriveLegal.ai, a specialized assistant for traffic laws and road safety worldwide. I cover India, USA, UK, UAE, Germany, Australia, Canada, and more. I cannot assist with topics outside my domain.",
                'data': {'type': 'rejection'},
                'confidence': 'High',
                'latency_ms': int((time.time() - start_time) * 1000)
            }

        # Session management
        if session_id not in self.chat_sessions:
            self.chat_sessions[session_id] = []

        context = self._get_context(message)
        
        # Try Gemini API
        if self.gemini_url and self.api_key:
            try:
                history = self.chat_sessions[session_id]
                
                # Inject context transparently
                full_prompt = message
                country_hint = ''
                if country_context:
                    country_hint = f"[USER LOCATION: The user is currently in {country_context.upper()}. Prioritize {country_context.upper()} traffic laws in your answer, but still answer about other countries if asked.]\n\n"
                if context:
                    full_prompt = f"{country_hint}{context}\n\nUser Question: {message}"
                elif country_hint:
                    full_prompt = f"{country_hint}User Question: {message}"
                
                # Base system message for Groq
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                
                # Append previous conversation history
                messages.extend(history)
                
                # Add current user prompt
                messages.append({"role": "user", "content": full_prompt})
                
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                }
                payload = {
                    "model": "llama3-8b-8192",
                    "messages": messages,
                    "temperature": 0.2,
                    "top_p": 0.8,
                    "max_tokens": 1024
                }
                
                req = requests.post(self.gemini_url, headers=headers, json=payload, timeout=15)
                
                if req.status_code != 200:
                    print(f"Groq API Error (HTTP {req.status_code}): {req.text}")
                    raise Exception(f"HTTP {req.status_code}")
                    
                resp_json = req.json()
                ai_text = resp_json['choices'][0]['message']['content']
                
                # Maintain manual history (append user then assistant)
                history.append({"role": "user", "content": message}) # Save original message without prompt injection
                history.append({"role": "assistant", "content": ai_text})
                
                return {
                    'text': ai_text.replace('**', ''), # Strip markdown bolding
                    'data': {'type': 'ai_response', 'source': 'groq-llama3'},
                    'confidence': 'High',
                    'latency_ms': int((time.time() - start_time) * 1000)
                }
            except Exception as e:
                print(f"Groq API Error: {e}. Falling back to rule-based engine.")

        # â”€â”€ OFFLINE RULE-BASED FALLBACK â”€â”€
        return self._process_fallback(message, session_id, start_time)

    def _process_fallback(self, message, session_id, start_time):
        """Rule-based fallback when offline or API fails."""
        msg = message.lower()
        
        if self.fallback_patterns['emergency'].search(msg):
            text = (
                "EMERGENCY CONTACTS (India):\n"
                "â€¢ Police: 100 or 112\n"
                "â€¢ Ambulance: 108\n"
                "â€¢ Highway Rescue: 1033\n"
                "If you are in an accident, move to safety, turn on hazard lights, and call 112 immediately."
            )
            return {'text': text, 'data': {'type': 'emergency'}, 'confidence': 'High', 'latency_ms': int((time.time() - start_time) * 1000)}
            
        if self.fallback_patterns['helmet'].search(msg):
            text = "Driving without a helmet is a violation of Section 129 of the Motor Vehicles Act. The national fine is Rs. 1000, and your license may be disqualified for 3 months."
            return {'text': text, 'data': {'violation_key': 'no_helmet'}, 'confidence': 'Medium', 'latency_ms': int((time.time() - start_time) * 1000)}

        if self.fallback_patterns['seatbelt'].search(msg):
            text = "Driving without a seatbelt violates Section 194B of the MV Act. The standard fine is Rs. 1000."
            return {'text': text, 'data': {'violation_key': 'no_seatbelt'}, 'confidence': 'Medium', 'latency_ms': int((time.time() - start_time) * 1000)}
            
        if self.fallback_patterns['drunk'].search(msg):
            text = "Drunk driving (BAC > 30mg/100ml) is a serious offense under Section 185. First offense: Rs. 10,000 fine and/or 6 months imprisonment. Repeat offense: Rs. 15,000 and/or 2 years imprisonment."
            return {'text': text, 'data': {'violation_key': 'drunk_driving'}, 'confidence': 'Medium', 'latency_ms': int((time.time() - start_time) * 1000)}
            
        if self.fallback_patterns['speeding'].search(msg):
            text = "Overspeeding falls under Section 183. Fines vary by vehicle type: Rs. 1000-2000 for Light Motor Vehicles (LMVs) and Rs. 2000-4000 for Medium/Heavy vehicles."
            return {'text': text, 'data': {'violation_key': 'overspeeding'}, 'confidence': 'Medium', 'latency_ms': int((time.time() - start_time) * 1000)}

        if self.fallback_patterns['license'].search(msg):
            text = "Driving without a valid license violates Section 3/181. The penalty is a fine of Rs. 5000."
            return {'text': text, 'data': {'violation_key': 'no_license'}, 'confidence': 'Medium', 'latency_ms': int((time.time() - start_time) * 1000)}
            
        if self.fallback_patterns['phone'].search(msg):
            text = "Using a mobile phone while driving is considered dangerous driving (Section 184). The fine is Rs. 1000-5000, and it may include imprisonment up to 1 year."
            return {'text': text, 'data': {'violation_key': 'mobile_phone'}, 'confidence': 'Medium', 'latency_ms': int((time.time() - start_time) * 1000)}
            
        if self.fallback_patterns['signal'].search(msg):
            text = "Jumping a red light is a violation of road regulations (Section 177/184). The typical fine ranges from Rs. 500 to Rs. 1000."
            return {'text': text, 'data': {'violation_key': 'red_light'}, 'confidence': 'Medium', 'latency_ms': int((time.time() - start_time) * 1000)}

        # Generic fallback
        text = "I am operating in offline mode. I can answer basic queries about common traffic violations like helmets, seatbelts, speeding, and drunk driving. What do you need help with?"
        return {
            'text': text,
            'data': {'type': 'generic_fallback'},
            'confidence': 'Low',
            'latency_ms': int((time.time() - start_time) * 1000)
        }


