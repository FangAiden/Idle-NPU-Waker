APP_ICON_SVG = b"""
<svg width="256" height="256" viewBox="0 0 256 256" fill="none" xmlns="http://www.w3.org/2000/svg">
<defs>
<linearGradient id="bgGrad" x1="0" y1="0" x2="256" y2="256" gradientUnits="userSpaceOnUse">
<stop stop-color="#1e3a8a"/>
<stop offset="1" stop-color="#0ea5e9"/>
</linearGradient>
</defs>

<rect width="256" height="256" rx="60" fill="url(#bgGrad)"/>

<g stroke="white" stroke-width="12" stroke-linecap="round" stroke-linejoin="round">
    <rect x="50" y="68" width="100" height="120" rx="16" />
    
    <path d="M70 68V48 M100 68V48 M130 68V48" />
    <path d="M70 188V208 M100 188V208 M130 188V208" />
    <path d="M50 88H30 M50 128H30 M50 168H30" />

    <rect x="74" y="92" width="52" height="72" rx="6" stroke-width="8"/>
    <path d="M90 92V164 M110 92V164 M74 116H126 M74 140H126" stroke-width="6"/>

    <path d="M180 80 C 200 100, 200 156, 180 176" />
    <path d="M210 60 C 240 90, 240 166, 210 196" />
</g>
</svg>
"""

AI_AVATAR_SVG = b"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <defs>
    <linearGradient id="aiGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0ea5e9;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#2563eb;stop-opacity:1" />
    </linearGradient>
  </defs>
  <circle cx="12" cy="12" r="12" fill="url(#aiGrad)"/>
  <rect x="7" y="8" width="10" height="9" rx="2" fill="white"/>
  <circle cx="10" cy="11.5" r="1.2" fill="#2563eb"/>
  <circle cx="14" cy="11.5" r="1.2" fill="#2563eb"/>
  <path d="M12 5V8M9 4L10 8M15 4L14 8" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

USER_AVATAR_SVG = b"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <circle cx="12" cy="12" r="12" fill="#4b5563"/>
  <path d="M12 11C13.6569 11 15 9.65685 15 8C15 6.34315 13.6569 5 12 5C10.3431 5 9 6.34315 9 8C9 9.65685 10.3431 11 12 11ZM12 13C8.68629 13 6 15.6863 6 19V20H18V19C18 15.6863 15.3137 13 12 13Z" fill="white"/>
</svg>
"""

COPY_ICON_SVG = b"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
</svg>
"""

CHEVRON_ICON_SVG = b"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 12 15 18 9"></polyline>
</svg>
"""

MORE_ICON_SVG = b"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <path d="M12 13C12.5523 13 13 12.5523 13 12C13 11.4477 12.5523 11 12 11C11.4477 11 11 11.4477 11 12C11 12.5523 11.4477 13 12 13Z" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M19 13C19.5523 13 20 12.5523 20 12C20 11.4477 19.5523 11 19 11C18.4477 11 18 11.4477 18 12C18 12.5523 18.4477 13 19 13Z" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M5 13C5.5523 13 6 12.5523 6 12C6 11.4477 5.5523 11 5 11C4.4477 11 4 11.4477 4 12C4 12.5523 4.4477 13 5 13Z" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""