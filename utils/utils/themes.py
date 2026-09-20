"""Session-scoped palettes shared by Plotly, the dashboard and HTML tables."""

THEMES = {
    "Light Mode": {
        "name": "light", "template": "plotly_white", "bg": "#EFF6FF",
        "bg_start": "#DBEAFE", "bg_end": "#FFFFFF",
        "surface": "#FFFFFF", "surface_alt": "#F3F7FD", "text": "#172B45",
        "muted": "#52647A", "border": "#D5E5F7", "grid": "#E8EEF5",
        "blue": "#2563EB", "green": "#087F70", "amber": "#AF5C08",
        "purple": "#7C3AED", "red": "#C52E59", "cyan": "#087F9C",
        "on_accent": "#FFFFFF", "scope": "#ECF3FF",
    },
    "Dark Mode": {
        "name": "dark", "template": "plotly_dark", "bg": "#0D1428",
        "bg_start": "#19345A", "bg_end": "#0D1428",
        "surface": "#151F36", "surface_alt": "#22304B", "text": "#F0F5FC",
        "muted": "#BBCADF", "border": "#3B4E68", "grid": "#2B3D55",
        "blue": "#67B5FF", "green": "#55E4BE", "amber": "#FFC36D",
        "purple": "#BEA2FF", "red": "#FF819D", "cyan": "#53DCF0",
        "on_accent": "#102135", "scope": "#1C3455",
    },
}


def get_theme(name="Light Mode"):
    return THEMES[name].copy()


def categorical_colors(theme):
    return [theme[key] for key in ("blue", "green", "purple", "amber", "cyan", "red")]


def dashboard_css(theme, animations=True):
    variables = ";".join(f"--lm-{key}:{value}" for key, value in theme.items() if value.startswith("#"))
    style = "<style>:root{" + variables + ";color-scheme:" + theme["name"] + ";}" + """
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stHeader"] {background:var(--lm-bg);color:var(--lm-text);}
    .stApp {font-family:Inter,"Segoe UI",sans-serif;}
    [data-testid="stHeader"] {background:color-mix(in srgb,var(--lm-bg) 92%,transparent);backdrop-filter:blur(16px);}
    .block-container {padding:4.5rem 2.5rem 2.5rem;max-width:1500px;}
    h1,h2,h3,h4,p,label,summary {color:inherit;}
    .stApp h1 {font-size:clamp(1.8rem,2.7vw,2.75rem);letter-spacing:-.045em;line-height:1.16;font-weight:750;}
    .stApp h2 {font-size:1.25rem;letter-spacing:-.025em;}
    .stApp h3 {font-size:1.05rem;letter-spacing:-.015em;}
    [data-testid="stSidebar"] {background:linear-gradient(175deg,var(--lm-surface),var(--lm-surface_alt));
        color:var(--lm-text);border-right:1px solid var(--lm-border);}
    [data-testid="stSidebarUserContent"] {padding-top:1.8rem;}
    [data-testid="stSidebar"] hr {margin:1.35rem 0;}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {font-size:.78rem;line-height:1.6;}
    [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"],
    [data-testid="stRadio"] label, [data-testid="stExpander"] {color:var(--lm-text)!important;}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {color:var(--lm-muted)!important;}
    [data-testid="stMetricValue"] {font-size:clamp(1.3rem,1.85vw,2rem);font-weight:750;
        letter-spacing:-.035em;font-variant-numeric:tabular-nums;}
    [data-testid="stMetricLabel"] {font-size:.78rem;font-weight:550;}
    [data-testid="stMetricLabel"] p {color:var(--lm-muted);}
    .eyebrow {font-size:.67rem;font-weight:700;letter-spacing:.17em;}
    .brand-lockup {display:flex;align-items:center;gap:12px;margin-bottom:1.9rem;}
    .brand-mark {display:grid;place-items:center;width:44px;height:44px;flex-shrink:0;border-radius:14px;
        background:linear-gradient(140deg,#2563EB,#123D99);color:#FFFFFF;font-size:.9rem;font-weight:800;
        box-shadow:0 5px 12px #2563EB26;letter-spacing:-.06em;}
    .brand {font-size:1.6rem;font-weight:800;letter-spacing:-.06em;line-height:1.2;color:var(--lm-text);}
    .brand span {color:var(--lm-blue);}
    .brand-sub {font-size:.55rem;font-weight:650;letter-spacing:.14em;color:var(--lm-muted);margin-top:5px;}
    .scope {display:flex;align-items:center;flex-wrap:wrap;gap:10px 20px;color:var(--lm-muted);
        padding:.7rem .15rem;font-size:.76rem;margin:.1rem 0 .6rem;}
    .scope span {overflow-wrap:anywhere;}
    .scope .scope-count {background:var(--lm-surface);border:1px solid var(--lm-border);
        color:var(--lm-blue);border-radius:24px;padding:7px 12px;font-weight:650;}
    .insight {border:1px solid var(--lm-border);padding:24px;margin-bottom:4px;min-height:230px;}
    .insight-heading {display:flex;align-items:center;gap:12px;margin-bottom:16px;}
    .insight-number {display:grid;place-items:center;width:34px;height:34px;flex-shrink:0;
        background:var(--lm-scope);color:var(--lm-blue);font-size:.75rem;font-weight:700;border-radius:10px;}
    .insight-title {font-weight:700;font-size:.88rem;letter-spacing:-.01em;}
    .insight p {font-size:.88rem;line-height:1.7;}
    .insight .action {font-size:.8rem;color:var(--lm-muted);margin:18px 0 0;padding-top:14px;border-top:1px solid var(--lm-border);}
    .insight .action strong {display:block;color:var(--lm-blue);font-size:.65rem;text-transform:uppercase;letter-spacing:.09em;margin-bottom:5px;}
    .footer {border-top:1px solid var(--lm-border);margin-top:20px;padding-top:20px;color:var(--lm-muted);font-size:.7rem;line-height:1.7;}
    hr {border-color:var(--lm-border)!important;}
    [data-testid="stTabs"] [role="tab"] {color:var(--lm-muted);}
    [data-testid="stTabs"] [data-baseweb="tab-highlight"],
    [data-testid="stTabs"] [data-baseweb="tab-border"] {display:none;}
    button {color:var(--lm-text)!important;}
    .stButton button,.stDownloadButton button,[data-testid="stBaseButton-secondary"] {
        background:var(--lm-surface);border-color:var(--lm-border);color:var(--lm-text);}
    .stButton button:hover,.stDownloadButton button:hover {border-color:var(--lm-blue)!important;}
    .stApp button:focus-visible,.stApp input:focus-visible {outline:2px solid var(--lm-blue);outline-offset:3px;}
    [data-testid="stDateInputField"], [data-testid="stMultiSelect"] [role="group"],
    [data-testid="stSelectbox"] [data-baseweb="select"]>div,
    [data-testid="stTextInput"] input,[data-baseweb="input"], [data-baseweb="select"]>div {
        background:var(--lm-surface)!important;color:var(--lm-text)!important;border-color:var(--lm-border)!important;border-radius:10px;}
    input,[role="spinbutton"],[role="combobox"] {color:var(--lm-text)!important;caret-color:var(--lm-text)!important;}
    [data-testid="stDateInput"] span {color:var(--lm-text)!important;}
    [data-testid="stTooltipIcon"], [data-testid="stTooltipIcon"] svg {color:var(--lm-muted)!important;}
    [data-testid="stMultiSelect"] [data-tag], [data-baseweb="tag"] {
        background:var(--lm-scope)!important;color:var(--lm-blue)!important;border-radius:6px;}
    [data-testid="stMultiSelect"] [data-tag] button {color:var(--lm-blue)!important;}
    [data-testid="stMultiSelect"] [data-tag] span {color:var(--lm-blue)!important;}
    [role="listbox"],[role="option"],[role="dialog"],[data-baseweb="popover"]>div,
    [data-baseweb="calendar"],[data-baseweb="menu"] {
        background:var(--lm-surface)!important;color:var(--lm-text)!important;}
    [role="option"][aria-selected="true"], [role="option"]:hover {
        background:var(--lm-scope)!important;color:var(--lm-text)!important;}
    [data-testid="stExpander"] details {background:var(--lm-surface);border-color:var(--lm-border);}
    [data-testid="stAlert"] {background:var(--lm-surface_alt);color:var(--lm-text);border:1px solid var(--lm-border);}
    /* Blue-to-white surfaces in light mode, with matching navy gradients in dark mode. */
    [data-testid="stMain"] {background-image:
        radial-gradient(ellipse at 95% 5%,color-mix(in srgb,var(--lm-blue) 6%,transparent),transparent 45%),
        linear-gradient(135deg,var(--lm-bg_start) 0%,var(--lm-bg) 38%,var(--lm-bg_end) 75%);
        background-attachment:fixed;}
    .st-key-dashboard_hero {position:relative;isolation:isolate;overflow:hidden;
        padding:32px 36px 28px;border:1px solid #3265B7;border-radius:24px;
        background:radial-gradient(ellipse at 100% 0%,#3075D9,transparent 65%),linear-gradient(115deg,#102C60,#194A99);
        box-shadow:0 12px 28px #123D991A;margin-bottom:4px;}
    .st-key-dashboard_hero::before {content:"";position:absolute;z-index:-1;right:-115px;top:-165px;
        width:430px;height:430px;border:1px solid #FFFFFF1F;border-radius:50%;
        box-shadow:0 0 0 48px #FFFFFF06,0 0 0 96px #FFFFFF04;pointer-events:none;}
    .st-key-dashboard_hero::after {content:"";position:absolute;z-index:-1;right:70px;bottom:-100px;width:260px;height:260px;
        border-radius:50%;background:radial-gradient(circle,#93C5FD25,transparent 70%);pointer-events:none;}
    .st-key-dashboard_hero h1 {color:#FFFFFF;max-width:720px;padding-top:8px;}
    .st-key-dashboard_hero [data-testid="stMarkdownContainer"] {color:#DCEAFF!important;}
    .st-key-dashboard_hero p {font-size:.92rem;max-width:600px;line-height:1.7;}
    .st-key-dashboard_hero .eyebrow {color:#BFDBFE;letter-spacing:.17em;}
    .hero-tags {display:flex;flex-wrap:wrap;gap:8px;margin-top:4px;}
    .hero-tags span {padding:5px 10px;border:1px solid #FFFFFF26;background:#FFFFFF0A;border-radius:20px;
        color:#E2EEFF;font-size:.65rem;letter-spacing:.025em;}
    .st-key-kpi_revenue {--lm-card-accent:var(--lm-blue);--lm-delay:0ms;}
    .st-key-kpi_profit {--lm-card-accent:var(--lm-green);--lm-delay:65ms;}
    .st-key-kpi_profit_margin {--lm-card-accent:var(--lm-purple);--lm-delay:130ms;}
    .st-key-kpi_return_rate {--lm-card-accent:var(--lm-amber);--lm-delay:195ms;}
    [data-testid="stMetric"] {border:1px solid var(--lm-border);border-top:2px solid var(--lm-card-accent,var(--lm-blue));
        border-radius:16px;padding:20px;min-height:125px;
        background:linear-gradient(145deg,var(--lm-surface) 60%,var(--lm-surface_alt));
        box-shadow:0 4px 14px #102C6005;}
    [data-testid="stMetricValue"] {color:var(--lm-text)!important;}
    .insight {border-radius:18px;background:var(--lm-surface);box-shadow:0 4px 16px #102C6004;}
    .insight-title {color:var(--lm-text);}
    [data-testid="stPlotlyChart"] {overflow:hidden;border:1px solid var(--lm-border);border-radius:18px;
        box-shadow:0 4px 16px #102C6005;}
    [data-testid="stTabs"] [role="tablist"] {gap:4px;padding:6px;background:var(--lm-surface_alt);
        border:1px solid var(--lm-border);border-radius:14px;}
    [data-testid="stTabs"] [role="tab"] {border-radius:9px;padding:10px 14px;height:auto;white-space:nowrap;}
    [data-testid="stTabs"] [role="tab"] p {font-size:.78rem;font-weight:550;}
    [data-testid="stTabs"] [role="tabpanel"] {padding-top:24px;}
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background:var(--lm-surface);color:var(--lm-blue)!important;
        box-shadow:0 2px 6px color-mix(in srgb,var(--lm-blue) 10%,transparent);}
    .stButton button,.stDownloadButton button {border-radius:10px;
        background:linear-gradient(110deg,color-mix(in srgb,var(--lm-blue) 8%,var(--lm-surface)),var(--lm-surface));}
    [data-testid="stSidebarCollapseButton"] *,[data-testid="stSidebarCollapsedControl"] * {color:var(--lm-muted)!important;}
    @media(hover:hover){[data-testid="stMetric"]:hover,.insight:hover {border-color:var(--lm-blue);
        box-shadow:0 8px 20px color-mix(in srgb,var(--lm-blue) 8%,transparent);}
        .stButton button:hover,.stDownloadButton button:hover {box-shadow:0 6px 16px color-mix(in srgb,var(--lm-blue) 16%,transparent);}}
    @media(max-width:1100px){.block-container{padding-left:1.5rem;padding-right:1.5rem;}
        [data-testid="stMetric"]{padding:16px 12px;}}
    @media(max-width:700px){.block-container{padding:4rem 1rem 1.2rem}.insight{min-height:0;padding:20px;}
        [data-testid="stMetricValue"]{font-size:1.8rem}.st-key-dashboard_hero{padding:24px 20px;border-radius:18px;}
        .st-key-dashboard_hero p{font-size:.85rem}.scope{gap:8px 12px;font-size:.7rem;}
        [data-testid="stTabs"] [role="tab"]{padding:9px 11px;}}
    """
    if animations:
        style += """
        @keyframes lm-enter {from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
        @keyframes lm-glow {0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(-30px,24px) scale(1.12)}}
        @media(prefers-reduced-motion:no-preference){
            .st-key-dashboard_hero {animation:lm-enter .55s ease-out both;}
            .st-key-dashboard_hero::after {animation:lm-glow 12s ease-in-out infinite;}
            [data-testid="stMetric"] {animation:lm-enter .5s ease-out var(--lm-delay,0ms) backwards;}
            [role="tabpanel"] [data-testid="stPlotlyChart"],[role="tabpanel"] .insight {animation:lm-enter .45s ease-out backwards;}
            [data-testid="stMetric"],.insight,[data-testid="stPlotlyChart"],.stButton button,.stDownloadButton button {
                transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease;}
            [data-testid="stTabs"] [role="tab"] {transition:background-color .2s ease,box-shadow .2s ease;}
            .js-plotly-plot .slice path {transition:filter .2s ease,opacity .2s ease;}
            @media(hover:hover){[data-testid="stMetric"]:hover,.insight:hover{transform:translateY(-3px)}
                .stButton button:hover,.stDownloadButton button:hover{transform:translateY(-1px)}
                .js-plotly-plot .slice:hover path{filter:brightness(1.08)}}
        }
        """
    # This is also emitted for the explicit off switch to stop active animations.
    off_rules = """.st-key-dashboard_hero,.st-key-dashboard_hero::after,[data-testid="stMetric"],
        .insight,[data-testid="stPlotlyChart"],.stButton button,.stDownloadButton button,
        [data-testid="stTabs"] [role="tab"],.js-plotly-plot .slice path {
            animation:none!important;transition:none!important;transform:none!important;}"""
    style += "@media(prefers-reduced-motion:reduce){" + off_rules + "}"
    if not animations:
        style += off_rules
    return style + "</style>"
