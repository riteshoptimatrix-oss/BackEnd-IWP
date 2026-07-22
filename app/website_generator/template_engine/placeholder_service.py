import html
from datetime import datetime
from typing import Dict, Any, List
from app.website_generator.schemas.payload import WebsiteGeneratorPayload
from app.website_generator.template_engine.theme_service import ThemeService
from app.website_generator.ai_content_engine.service import AIContentService

class PlaceholderService:
    """
    Placeholder Engine replacing {{key}} tokens with sanitized AI content & category components.
    Layout remains 100% template-driven while content copy & category widgets are rendered dynamically.
    """
    @staticmethod
    def _sanitize(val: Any) -> str:
        if val is None:
            return ""
        return html.escape(str(val))

    @classmethod
    def generate_context(cls, payload: WebsiteGeneratorPayload) -> Dict[str, str]:
        info = payload.businessInfo

        full_address = f"{info.fullAddress}, {info.city}, {info.state} - {info.pincode}, {info.country}"
        theme_class = ThemeService.get_theme_class(payload.theme)

        # Generate AI copy (Hero, About, Services, FAQ, SEO, Footer, Contact)
        ai_content = AIContentService.generate_content(payload.dict())

        # Logo HTML
        logo_html = (
            f'<img src="{info.logoUrl}" alt="{cls._sanitize(info.companyName)} Logo" style="height:36px; width:auto;" />'
            if info.logoUrl
            else '<div style="height:36px; width:36px; border-radius:10px; background:var(--accent-color); color:var(--accent-text); display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:1.1rem;">⚡</div>'
        )

        # AI Services HTML cards
        services_cards_html = "".join([
            f'<div class="card"><h3>{cls._sanitize(item.title)}</h3><p>{cls._sanitize(item.description)}</p></div>'
            for item in ai_content.services
        ])

        # Features HTML cards
        features_cards_html = "".join([
            f'<div class="card"><h3>✔ {cls._sanitize(feat)}</h3><p>Fully enabled and optimized for {cls._sanitize(info.companyName)}.</p></div>'
            for feat in payload.selectedFeatures
        ])

        # Social links HTML
        social_html_parts = []
        if info.socialLinks:
            soc = info.socialLinks
            if soc.facebook:
                social_html_parts.append(f'<a href="{cls._sanitize(soc.facebook)}" target="_blank">Facebook</a>')
            if soc.instagram:
                social_html_parts.append(f'<a href="{cls._sanitize(soc.instagram)}" target="_blank">Instagram</a>')
            if soc.linkedin:
                social_html_parts.append(f'<a href="{cls._sanitize(soc.linkedin)}" target="_blank">LinkedIn</a>')
            if soc.twitter:
                social_html_parts.append(f'<a href="{cls._sanitize(soc.twitter)}" target="_blank">Twitter/X</a>')
            if soc.youtube:
                social_html_parts.append(f'<a href="{cls._sanitize(soc.youtube)}" target="_blank">YouTube</a>')

        social_links_html = " | ".join(social_html_parts) if social_html_parts else "Follow us on social media"

        # --- Category Specific HTML Widgets ---

        # 1. Restaurant Menu HTML
        restaurant_menu_html = """
        <div class="menu-grid" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:1.5rem; margin-top:2rem;">
          <div class="card">
            <div style="display:flex; justify-between:space-between; font-weight:bold;">
              <span style="font-size:1.1rem;">Chef's Special Truffle Pasta</span>
              <span style="color:var(--accent-color);">$24.00</span>
            </div>
            <p style="font-size:0.85rem; opacity:0.8; margin-top:0.5rem;">Handcrafted tagliatelle with wild forest mushrooms and black truffle cream sauce.</p>
          </div>
          <div class="card">
            <div style="display:flex; justify-between:space-between; font-weight:bold;">
              <span style="font-size:1.1rem;">Wood-Fired Margherita Pizza</span>
              <span style="color:var(--accent-color);">$18.50</span>
            </div>
            <p style="font-size:0.85rem; opacity:0.8; margin-top:0.5rem;">San Marzano tomatoes, fresh buffalo mozzarella, and organic basil leaves.</p>
          </div>
          <div class="card">
            <div style="display:flex; justify-between:space-between; font-weight:bold;">
              <span style="font-size:1.1rem;">Artisanal Salmon Steak</span>
              <span style="color:var(--accent-color);">$29.00</span>
            </div>
            <p style="font-size:0.85rem; opacity:0.8; margin-top:0.5rem;">Pan-seared Atlantic salmon served with asparagus spear and lemon butter drizzle.</p>
          </div>
        </div>
        """

        # 2. Reservation Form HTML
        reservation_form_html = f"""
        <form class="card" style="max-w:500px; margin:2rem auto; display:flex; flex-direction:column; gap:1rem;" onsubmit="event.preventDefault(); alert('Reservation Request Submitted to {cls._sanitize(info.companyName)}!');">
          <h3>Reserve Your Table</h3>
          <input type="text" placeholder="Full Name" required style="padding:0.75rem; border-radius:8px; border:1px solid #ccc;" />
          <input type="email" placeholder="Email Address" required style="padding:0.75rem; border-radius:8px; border:1px solid #ccc;" />
          <div style="display:flex; gap:1rem;">
            <input type="date" required style="flex:1; padding:0.75rem; border-radius:8px; border:1px solid #ccc;" />
            <input type="time" required style="flex:1; padding:0.75rem; border-radius:8px; border:1px solid #ccc;" />
          </div>
          <select style="padding:0.75rem; border-radius:8px; border:1px solid #ccc;">
            <option>2 Guests</option>
            <option>4 Guests</option>
            <option>6 Guests</option>
            <option>Private Event (8+ Guests)</option>
          </select>
          <button type="submit" style="padding:0.85rem; background:var(--accent-color); color:#fff; font-weight:bold; border:none; border-radius:8px; cursor:pointer;">Confirm Reservation</button>
        </form>
        """

        # 3. Gym BMI Calculator HTML
        bmi_calculator_html = """
        <div class="card" style="max-width:450px; margin:2rem auto; text-align:center;">
          <h3>Interactive BMI Calculator</h3>
          <p style="font-size:0.85rem; opacity:0.8; margin-bottom:1rem;">Calculate your Body Mass Index and start your fitness journey today.</p>
          <div style="display:flex; flex-direction:column; gap:0.75rem;">
            <input id="bmi-weight" type="number" placeholder="Weight (kg)" style="padding:0.75rem; border-radius:8px; border:1px solid #ccc;" />
            <input id="bmi-height" type="number" placeholder="Height (cm)" style="padding:0.75rem; border-radius:8px; border:1px solid #ccc;" />
            <button type="button" onclick="const w=parseFloat(document.getElementById('bmi-weight').value); const h=parseFloat(document.getElementById('bmi-height').value)/100; if(w&&h){const bmi=(w/(h*h)).toFixed(1); alert('Your BMI is ' + bmi);} else {alert('Please enter weight and height');}" style="padding:0.85rem; background:var(--accent-color); color:#fff; font-weight:bold; border:none; border-radius:8px; cursor:pointer;">Calculate BMI</button>
          </div>
        </div>
        """

        # 4. Doctor Appointment Form HTML
        medical_appointment_form_html = f"""
        <form class="card" style="max-w:550px; margin:2rem auto; display:flex; flex-direction:column; gap:1rem;" onsubmit="event.preventDefault(); alert('Medical Appointment Request Received at {cls._sanitize(info.companyName)}!');">
          <h3>Book Doctor Appointment</h3>
          <input type="text" placeholder="Patient Full Name" required style="padding:0.75rem; border-radius:8px; border:1px solid #ccc;" />
          <input type="tel" placeholder="Contact Phone" required style="padding:0.75rem; border-radius:8px; border:1px solid #ccc;" />
          <select style="padding:0.75rem; border-radius:8px; border:1px solid #ccc;">
            <option>Cardiology Department</option>
            <option>Neurology & Spine</option>
            <option>Pediatric Care</option>
            <option>Orthopedics & Sports Medicine</option>
            <option>General Consultation</option>
          </select>
          <input type="date" required style="padding:0.75rem; border-radius:8px; border:1px solid #ccc;" />
          <button type="submit" style="padding:0.85rem; background:var(--accent-color); color:#fff; font-weight:bold; border:none; border-radius:8px; cursor:pointer;">Schedule Appointment</button>
        </form>
        """

        # 5. Property Listings Grid HTML
        property_grid_html = """
        <div class="property-grid" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:1.5rem; margin-top:2rem;">
          <div class="card">
            <div style="height:180px; background:#e2e8f0; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold; color:#64748b;">Luxury Penthouse Suite</div>
            <h3 style="margin-top:1rem;">Skyline Luxury Villa</h3>
            <p style="font-size:0.85rem; opacity:0.8;">4 Beds • 3 Baths • 3,200 SqFt</p>
            <p style="font-size:1.2rem; font-weight:extrabold; color:var(--accent-color); margin-top:0.5rem;">$1,250,000</p>
          </div>
          <div class="card">
            <div style="height:180px; background:#cbd5e1; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold; color:#475569;">Modern Suburban Home</div>
            <h3 style="margin-top:1rem;">Meadowbrook Estate</h3>
            <p style="font-size:0.85rem; opacity:0.8;">3 Beds • 2.5 Baths • 2,400 SqFt</p>
            <p style="font-size:1.2rem; font-weight:extrabold; color:var(--accent-color); margin-top:0.5rem;">$780,000</p>
          </div>
        </div>
        """

        # 6. SaaS Code Snippet HTML
        code_snippet_html = """
        <div class="card" style="background:#0f172a; color:#f8fafc; font-family:monospace; padding:1.5rem; border-radius:12px; margin-top:2rem;">
          <div style="display:flex; justify-content:space-between; margin-bottom:1rem; opacity:0.6; font-size:0.8rem;">
            <span>curl -X POST https://api.cloudplatform.io/v1/deploy</span>
            <span>Bash</span>
          </div>
          <pre style="margin:0; overflow-x:auto;"><code>curl -H "Authorization: Bearer api_key" \\
     -d '{"environment": "production", "autoscale": true}'</code></pre>
        </div>
        """

        return {
            "{{company_name}}": cls._sanitize(info.companyName),
            "{{business_description}}": cls._sanitize(ai_content.about.overview),
            "{{category}}": cls._sanitize(info.category),
            "{{phone}}": cls._sanitize(info.phone),
            "{{email}}": cls._sanitize(info.email),
            "{{address}}": cls._sanitize(full_address),
            "{{working_hours}}": cls._sanitize(info.workingHours),
            "{{hero_title}}": cls._sanitize(ai_content.hero.title),
            "{{hero_subtitle}}": cls._sanitize(ai_content.hero.subtitle),
            "{{hero_cta_text}}": cls._sanitize(ai_content.hero.cta_text),
            "{{hero_cta_link}}": cls._sanitize(ai_content.hero.cta_link),
            "{{footer_slogan}}": cls._sanitize(ai_content.footer.slogan),
            "{{theme_class}}": theme_class,
            "{{year}}": str(datetime.now().year),
            "{{logo_html}}": logo_html,
            "{{services_cards_html}}": services_cards_html,
            "{{features_cards_html}}": features_cards_html,
            "{{social_links_html}}": social_links_html,
            "{{restaurant_menu_html}}": restaurant_menu_html,
            "{{reservation_form_html}}": reservation_form_html,
            "{{bmi_calculator_html}}": bmi_calculator_html,
            "{{medical_appointment_form_html}}": medical_appointment_form_html,
            "{{property_grid_html}}": property_grid_html,
            "{{code_snippet_html}}": code_snippet_html,
        }

    @classmethod
    def render_content(cls, content: str, context: Dict[str, str]) -> str:
        for placeholder, value in context.items():
            content = content.replace(placeholder, value)
        return content
