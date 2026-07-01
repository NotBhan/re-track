<!-- Design System -->
<!DOCTYPE html>

<html class="dark" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>AndesContext - Repositories</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=JetBrains+Mono:wght@400;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    "colors": {
                        "outline-variant": "#424754",
                        "surface-container-lowest": "#0b0e15",
                        "on-secondary-fixed": "#002113",
                        "primary-fixed-dim": "#adc6ff",
                        "primary": "#adc6ff",
                        "secondary-fixed": "#6ffbbe",
                        "on-error-container": "#ffdad6",
                        "surface-dim": "#10131a",
                        "on-error": "#690005",
                        "secondary-fixed-dim": "#4edea3",
                        "error": "#ffb4ab",
                        "surface-variant": "#32353c",
                        "background": "#10131a",
                        "surface-bright": "#363941",
                        "on-primary": "#002e6a",
                        "primary-fixed": "#d8e2ff",
                        "on-surface": "#e1e2ec",
                        "error-container": "#93000a",
                        "surface-container-highest": "#32353c",
                        "outline": "#8c909f",
                        "tertiary-container": "#ca8100",
                        "inverse-on-surface": "#2e3038",
                        "surface-tint": "#adc6ff",
                        "on-primary-fixed-variant": "#004395",
                        "on-tertiary-container": "#3e2400",
                        "on-primary-fixed": "#001a42",
                        "secondary-container": "#00a572",
                        "primary-container": "#4d8eff",
                        "surface-container-high": "#272a31",
                        "on-tertiary-fixed": "#2a1700",
                        "on-secondary-fixed-variant": "#005236",
                        "secondary": "#4edea3",
                        "surface-container-low": "#191b23",
                        "surface": "#10131a",
                        "tertiary-fixed-dim": "#ffb95f",
                        "on-tertiary-fixed-variant": "#653e00",
                        "tertiary": "#ffb95f",
                        "tertiary-fixed": "#ffddb8",
                        "surface-container": "#1d2027",
                        "on-tertiary": "#472a00",
                        "on-secondary-container": "#00311f",
                        "on-primary-container": "#00285d",
                        "inverse-surface": "#e1e2ec",
                        "on-surface-variant": "#c2c6d6",
                        "inverse-primary": "#005ac2",
                        "on-background": "#e1e2ec",
                        "on-secondary": "#003824"
                    },
                    "borderRadius": {
                        "DEFAULT": "0.25rem",
                        "lg": "0.5rem",
                        "xl": "0.75rem",
                        "full": "9999px"
                    },
                    "spacing": {
                        "gutter": "16px",
                        "stack-gap": "12px",
                        "component-gap-sm": "8px",
                        "container-margin": "24px",
                        "card-padding": "20px",
                        "sidebar-width": "240px"
                    },
                    "fontFamily": {
                        "body-md": ["Inter"],
                        "label-sm": ["Inter"],
                        "status-dot": ["JetBrains Mono"],
                        "headline-md": ["Inter"],
                        "display": ["Inter"],
                        "headline-lg": ["Inter"],
                        "body-lg": ["Inter"],
                        "code-md": ["JetBrains Mono"]
                    },
                    "fontSize": {
                        "body-md": ["14px", { "lineHeight": "20px", "fontWeight": "400" }],
                        "label-sm": ["12px", { "lineHeight": "16px", "letterSpacing": "0.02em", "fontWeight": "500" }],
                        "status-dot": ["11px", { "lineHeight": "12px", "fontWeight": "700" }],
                        "headline-md": ["20px", { "lineHeight": "28px", "fontWeight": "500" }],
                        "display": ["32px", { "lineHeight": "40px", "letterSpacing": "-0.02em", "fontWeight": "600" }],
                        "headline-lg": ["24px", { "lineHeight": "32px", "letterSpacing": "-0.01em", "fontWeight": "600" }],
                        "body-lg": ["16px", { "lineHeight": "24px", "fontWeight": "400" }],
                        "code-md": ["13px", { "lineHeight": "20px", "fontWeight": "400" }]
                    }
                }
            }
        }
    </script>
<style>
        body {
            background-color: #020617; /* Canvas Level 0 */
            color: #e1e2ec;
        }
        .card-surface {
            background-color: #0F172A; /* Level 1 */
            border: 1px solid #1E293B;
        }
        .card-interactive:hover {
            transform: scale(1.01);
            border-color: #32353c; /* outline-variant approximation */
            box-shadow: 0 0 15px rgba(173, 198, 255, 0.05); /* Soft primary glow */
        }
    </style>
</head>
<body class="font-body-md text-body-md text-on-surface antialiased flex h-screen overflow-hidden">
<!-- SideNavBar -->
<nav class="w-sidebar-width h-screen fixed left-0 top-0 bg-surface-container-low dark:bg-surface-container-lowest border-r border-outline-variant flex flex-col h-full py-6 px-4 z-20">
<div class="mb-8 px-3">
<h1 class="text-headline-md font-headline-md font-bold tracking-tight text-on-surface dark:text-on-surface">AndesContext</h1>
<p class="font-label-sm text-label-sm text-on-surface-variant">AI-Native Memory</p>
</div>
<button class="mb-6 w-full bg-[#3B82F6] text-white hover:bg-primary-container font-label-sm text-label-sm rounded-lg py-2.5 px-4 flex items-center justify-center gap-2 transition-colors">
<span class="material-symbols-outlined text-[18px]">add</span>
            New Index
        </button>
<div class="flex-1 space-y-1">
<a class="flex items-center gap-3 py-2 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 rounded-md hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">dashboard</span>
<span class="font-label-sm text-label-sm">Dashboard</span>
</a>
<a class="flex items-center gap-3 py-2 text-primary dark:text-primary font-bold border-l-2 border-primary pl-3 rounded-r-md hover:bg-surface-container-high transition-colors duration-200 bg-surface-container-high/50" href="#">
<span class="material-symbols-outlined text-[20px]">folder_open</span>
<span class="font-label-sm text-label-sm">Repositories</span>
</a>
<a class="flex items-center gap-3 py-2 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 rounded-md hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">auto_awesome_motion</span>
<span class="font-label-sm text-label-sm">Context Builder</span>
</a>
<a class="flex items-center gap-3 py-2 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 rounded-md hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">memory</span>
<span class="font-label-sm text-label-sm">Memory</span>
</a>
<a class="flex items-center gap-3 py-2 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 rounded-md hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">query_stats</span>
<span class="font-label-sm text-label-sm">Benchmarks</span>
</a>
<a class="flex items-center gap-3 py-2 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 rounded-md hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">settings</span>
<span class="font-label-sm text-label-sm">Settings</span>
</a>
</div>
<div class="mt-auto border-t border-outline-variant pt-4 space-y-3 font-status-dot text-status-dot text-on-surface-variant">
<div class="flex items-center gap-2 pl-3">
<span class="material-symbols-outlined text-[16px]">sensors</span>
<span>Backend: Online</span>
<div class="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] ml-auto mr-2"></div>
</div>
<div class="flex items-center gap-2 pl-3">
<span class="material-symbols-outlined text-[16px]">memory</span>
<span>Ollama: Running</span>
<div class="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(173,198,255,0.5)] ml-auto mr-2 animate-pulse"></div>
</div>
<div class="flex items-center gap-2 pl-3">
<span class="material-symbols-outlined text-[16px]">psychology</span>
<span>Cognee: Idle</span>
<div class="w-2 h-2 rounded-full bg-slate-500 ml-auto mr-2"></div>
</div>
</div>
</nav>
<!-- Main Content Wrapper -->
<div class="ml-sidebar-width flex-1 flex flex-col h-full relative">
<!-- TopAppBar -->
<header class="h-16 w-full sticky top-0 z-10 bg-surface dark:bg-surface flex items-center justify-between px-gutter">
<div class="flex items-center gap-4 flex-1">
<div class="relative w-96">
<span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">search</span>
<input class="w-full bg-transparent border-b border-transparent focus:border-primary border-t-0 border-x-0 outline-none text-on-surface font-body-md text-body-md pl-10 py-2 focus:ring-0 transition-colors placeholder:text-on-surface-variant/50" placeholder="Search repositories..." type="text"/>
</div>
</div>
<div class="flex items-center gap-2">
<button class="text-on-surface-variant hover:bg-surface-variant rounded-full p-2 transition-all active:scale-95 duration-150">
<span class="material-symbols-outlined">notifications</span>
</button>
<button class="text-on-surface-variant hover:bg-surface-variant rounded-full p-2 transition-all active:scale-95 duration-150">
<span class="material-symbols-outlined">account_circle</span>
</button>
</div>
</header>
<!-- Main Workspace -->
<main class="flex-1 flex overflow-hidden p-container-margin gap-6">
<!-- Grid of Repos -->
<div class="flex-1 overflow-y-auto pr-2 custom-scrollbar">
<div class="flex justify-between items-center mb-6">
<h2 class="font-headline-lg text-headline-lg text-on-surface">Active Repositories</h2>
<div class="flex gap-2">
<button class="border border-outline-variant bg-transparent hover:bg-surface-variant text-on-surface font-label-sm text-label-sm rounded px-3 py-1.5 transition-colors flex items-center gap-2">
<span class="material-symbols-outlined text-[16px]">filter_list</span> Filter
                        </button>
<button class="border border-outline-variant bg-transparent hover:bg-surface-variant text-on-surface font-label-sm text-label-sm rounded px-3 py-1.5 transition-colors flex items-center gap-2">
<span class="material-symbols-outlined text-[16px]">sort</span> Sort
                        </button>
</div>
</div>
<div class="grid grid-cols-1 xl:grid-cols-2 gap-stack-gap">
<!-- Repo Card 1 (Selected) -->
<div class="card-surface rounded-xl p-card-padding card-interactive transition-all border-primary shadow-[0_0_15px_rgba(173,198,255,0.1)] relative overflow-hidden group cursor-pointer">
<div class="flex justify-between items-start mb-4">
<div>
<h3 class="font-headline-md text-headline-md text-primary flex items-center gap-2">
<span class="material-symbols-outlined">folder</span>
                                    andes-core-engine
                                </h3>
<p class="font-code-md text-code-md text-on-surface-variant mt-1">~/dev/projects/andes-core-engine</p>
</div>
<div class="flex gap-1">
<span class="bg-surface-variant px-2 py-1 rounded text-[10px] font-bold text-[#3178C6]">TS</span>
<span class="bg-surface-variant px-2 py-1 rounded text-[10px] font-bold text-[#DEA584]">RS</span>
</div>
</div>
<div class="grid grid-cols-3 gap-4 mb-6">
<div>
<p class="font-label-sm text-label-sm text-on-surface-variant">Files</p>
<p class="font-body-md text-body-md text-on-surface">1,245</p>
</div>
<div>
<p class="font-label-sm text-label-sm text-on-surface-variant">Memory Size</p>
<p class="font-body-md text-body-md text-on-surface">4.2 GB</p>
</div>
<div>
<p class="font-label-sm text-label-sm text-on-surface-variant">Last Indexed</p>
<p class="font-body-md text-body-md text-on-surface">2 hrs ago</p>
</div>
</div>
<div class="flex gap-2">
<button class="flex-1 bg-surface-variant hover:bg-surface-bright text-on-surface font-label-sm text-label-sm rounded py-1.5 transition-colors flex items-center justify-center gap-1">
<span class="material-symbols-outlined text-[16px]">sync</span> Re-index
                            </button>
<button class="bg-surface-variant hover:bg-error-container hover:text-on-error-container text-on-surface font-label-sm text-label-sm rounded px-3 py-1.5 transition-colors">
<span class="material-symbols-outlined text-[16px]">delete</span>
</button>
</div>
</div>
<!-- Repo Card 2 -->
<div class="card-surface rounded-xl p-card-padding card-interactive transition-all relative overflow-hidden group cursor-pointer">
<div class="flex justify-between items-start mb-4">
<div>
<h3 class="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
<span class="material-symbols-outlined">folder</span>
                                    auth-service-go
                                </h3>
<p class="font-code-md text-code-md text-on-surface-variant mt-1">~/dev/services/auth-service</p>
</div>
<div class="flex gap-1">
<span class="bg-surface-variant px-2 py-1 rounded text-[10px] font-bold text-[#00ADD8]">GO</span>
</div>
</div>
<div class="grid grid-cols-3 gap-4 mb-6">
<div>
<p class="font-label-sm text-label-sm text-on-surface-variant">Files</p>
<p class="font-body-md text-body-md text-on-surface">84</p>
</div>
<div>
<p class="font-label-sm text-label-sm text-on-surface-variant">Memory Size</p>
<p class="font-body-md text-body-md text-on-surface">156 MB</p>
</div>
<div>
<p class="font-label-sm text-label-sm text-on-surface-variant">Last Indexed</p>
<p class="font-body-md text-body-md text-on-surface">1 day ago</p>
</div>
</div>
<div class="flex gap-2">
<button class="flex-1 border border-outline-variant hover:border-primary text-on-surface font-label-sm text-label-sm rounded py-1.5 transition-colors flex items-center justify-center gap-1">
<span class="material-symbols-outlined text-[16px]">play_arrow</span> Index
                            </button>
<button class="bg-transparent hover:bg-surface-variant text-on-surface font-label-sm text-label-sm rounded px-3 py-1.5 transition-colors">
<span class="material-symbols-outlined text-[16px]">more_vert</span>
</button>
</div>
</div>
</div>
</div>
<!-- Right Panel: Context Details -->
<aside class="w-[400px] flex-shrink-0 card-surface rounded-xl flex flex-col overflow-hidden h-full">
<div class="p-card-padding border-b border-outline-variant bg-surface-container-low">
<div class="flex justify-between items-start mb-2">
<h3 class="font-headline-md text-headline-md text-on-surface">andes-core-engine</h3>
<button class="text-on-surface-variant hover:text-on-surface"><span class="material-symbols-outlined text-[20px]">close</span></button>
</div>
<div class="flex items-center gap-2 font-code-md text-code-md text-primary">
<span class="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
                        Index Healthy
                    </div>
</div>
<div class="flex-1 overflow-y-auto p-card-padding space-y-6 custom-scrollbar">
<section>
<h4 class="font-label-sm text-label-sm text-on-surface-variant mb-2 uppercase tracking-wider">Purpose</h4>
<p class="font-body-md text-body-md text-on-surface bg-surface-container-lowest p-3 rounded border border-outline-variant/50">
                            Core processing engine for local AI memory graph construction. Handles file parsing, embedding generation, and initial vector storage.
                        </p>
</section>
<section>
<h4 class="font-label-sm text-label-sm text-on-surface-variant mb-2 uppercase tracking-wider">Architecture</h4>
<div class="bg-surface-container-lowest p-3 rounded border border-outline-variant/50 space-y-2">
<div class="flex items-center gap-2"><span class="material-symbols-outlined text-primary text-[16px]">account_tree</span> <span class="font-body-md text-body-md text-on-surface">Event-driven microkernel</span></div>
<div class="flex items-center gap-2"><span class="material-symbols-outlined text-primary text-[16px]">database</span> <span class="font-body-md text-body-md text-on-surface">Local SQLite + LanceDB</span></div>
</div>
</section>
<section>
<h4 class="font-label-sm text-label-sm text-on-surface-variant mb-2 uppercase tracking-wider">Key Components</h4>
<ul class="space-y-2">
<li class="font-code-md text-code-md text-on-surface bg-surface-variant px-2 py-1.5 rounded flex justify-between">
<span>src/parser/ast.rs</span>
<span class="text-on-surface-variant">High Centrality</span>
</li>
<li class="font-code-md text-code-md text-on-surface bg-surface-variant px-2 py-1.5 rounded flex justify-between">
<span>src/embedding/worker.ts</span>
<span class="text-on-surface-variant">Hot Path</span>
</li>
</ul>
</section>
</div>
</aside>
</main>
</div>
<style>
        /* Minimal custom scrollbar for webkit */
        .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
            background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background-color: #32353c; /* surface-variant */
            border-radius: 20px;
        }
    </style>
</body></html>

<!-- Repositories - AndesContext -->
<!DOCTYPE html>

<html class="dark" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>AndesContext - Context Builder</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;700&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap" rel="stylesheet"/>
<script id="tailwind-config">
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    colors: {
                        "outline-variant": "#424754",
                        "surface-container-lowest": "#0b0e15",
                        "on-secondary-fixed": "#002113",
                        "primary-fixed-dim": "#adc6ff",
                        "primary": "#adc6ff",
                        "secondary-fixed": "#6ffbbe",
                        "on-error-container": "#ffdad6",
                        "surface-dim": "#10131a",
                        "on-error": "#690005",
                        "secondary-fixed-dim": "#4edea3",
                        "error": "#ffb4ab",
                        "surface-variant": "#32353c",
                        "background": "#10131a",
                        "surface-bright": "#363941",
                        "on-primary": "#002e6a",
                        "primary-fixed": "#d8e2ff",
                        "on-surface": "#e1e2ec",
                        "error-container": "#93000a",
                        "surface-container-highest": "#32353c",
                        "outline": "#8c909f",
                        "tertiary-container": "#ca8100",
                        "inverse-on-surface": "#2e3038",
                        "surface-tint": "#adc6ff",
                        "on-primary-fixed-variant": "#004395",
                        "on-tertiary-container": "#3e2400",
                        "on-primary-fixed": "#001a42",
                        "secondary-container": "#00a572",
                        "primary-container": "#4d8eff",
                        "surface-container-high": "#272a31",
                        "on-tertiary-fixed": "#2a1700",
                        "on-secondary-fixed-variant": "#005236",
                        "secondary": "#4edea3",
                        "surface-container-low": "#191b23",
                        "surface": "#10131a",
                        "tertiary-fixed-dim": "#ffb95f",
                        "on-tertiary-fixed-variant": "#653e00",
                        "tertiary": "#ffb95f",
                        "tertiary-fixed": "#ffddb8",
                        "surface-container": "#1d2027",
                        "on-tertiary": "#472a00",
                        "on-secondary-container": "#00311f",
                        "on-primary-container": "#00285d",
                        "inverse-surface": "#e1e2ec",
                        "on-surface-variant": "#c2c6d6",
                        "inverse-primary": "#005ac2",
                        "on-background": "#e1e2ec",
                        "on-secondary": "#003824"
                    },
                    borderRadius: {
                        DEFAULT: "0.25rem",
                        lg: "0.5rem",
                        xl: "0.75rem",
                        full: "9999px"
                    },
                    spacing: {
                        gutter: "16px",
                        "stack-gap": "12px",
                        "component-gap-sm": "8px",
                        "container-margin": "24px",
                        "card-padding": "20px",
                        "sidebar-width": "240px"
                    },
                    fontFamily: {
                        "body-md": ["Inter"],
                        "label-sm": ["Inter"],
                        "status-dot": ["JetBrains Mono"],
                        "headline-md": ["Inter"],
                        display: ["Inter"],
                        "headline-lg": ["Inter"],
                        "body-lg": ["Inter"],
                        "code-md": ["JetBrains Mono"]
                    },
                    fontSize: {
                        "body-md": ["14px", { lineHeight: "20px", fontWeight: "400" }],
                        "label-sm": ["12px", { lineHeight: "16px", letterSpacing: "0.02em", fontWeight: "500" }],
                        "status-dot": ["11px", { lineHeight: "12px", fontWeight: "700" }],
                        "headline-md": ["20px", { lineHeight: "28px", fontWeight: "500" }],
                        display: ["32px", { lineHeight: "40px", letterSpacing: "-0.02em", fontWeight: "600" }],
                        "headline-lg": ["24px", { lineHeight: "32px", letterSpacing: "-0.01em", fontWeight: "600" }],
                        "body-lg": ["16px", { lineHeight: "24px", fontWeight: "400" }],
                        "code-md": ["13px", { lineHeight: "20px", fontWeight: "400" }]
                    }
                }
            }
        };
    </script>
<style>
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }
        
        .glow-pulse {
            animation: pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        @keyframes pulse-glow {
            0%, 100% {
                opacity: 1;
                box-shadow: 0 0 15px rgba(59, 130, 246, 0.2);
            }
            50% {
                opacity: .5;
                box-shadow: 0 0 30px rgba(59, 130, 246, 0.5);
            }
        }
        
        .pipeline-line {
            position: absolute;
            left: 15px;
            top: 24px;
            bottom: 24px;
            width: 2px;
            background: linear-gradient(to bottom, #adc6ff 50%, #424754 50%);
            background-size: 100% 200%;
            animation: slide-gradient 2s linear infinite;
        }
        
        @keyframes slide-gradient {
            0% { background-position: 100% -100%; }
            100% { background-position: 100% 100%; }
        }
    </style>
</head>
<body class="bg-surface-container-lowest text-on-surface font-body-md h-screen overflow-hidden flex">
<!-- SideNavBar (from JSON) -->
<nav class="w-sidebar-width h-screen fixed left-0 top-0 bg-surface-container-low dark:bg-surface-container-lowest border-r border-outline-variant flex flex-col py-6 px-4 z-20">
<div class="mb-8">
<div class="flex items-center gap-3">
<div class="w-8 h-8 rounded bg-primary/20 flex items-center justify-center text-primary">
<span class="material-symbols-outlined">auto_awesome_motion</span>
</div>
<div>
<h1 class="text-headline-md font-headline-md font-bold tracking-tight text-on-surface dark:text-on-surface">AndesContext</h1>
<p class="text-label-sm font-label-sm text-on-surface-variant">AI-Native Memory</p>
</div>
</div>
</div>
<button class="mb-6 w-full bg-primary hover:bg-primary-container text-on-primary py-2 rounded-lg font-label-sm text-label-sm flex items-center justify-center gap-2 transition-colors">
<span class="material-symbols-outlined" style="font-size: 18px;">add</span>
            New Index
        </button>
<div class="flex-1 space-y-2">
<a class="flex items-center gap-3 py-2 rounded-lg text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined">dashboard</span>
<span class="font-label-sm text-label-sm">Dashboard</span>
</a>
<a class="flex items-center gap-3 py-2 rounded-lg text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined">folder_open</span>
<span class="font-label-sm text-label-sm">Repositories</span>
</a>
<a class="flex items-center gap-3 py-2 rounded-lg text-primary dark:text-primary font-bold border-l-2 border-primary pl-3 bg-primary/10" href="#">
<span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">auto_awesome_motion</span>
<span class="font-label-sm text-label-sm">Context Builder</span>
</a>
<a class="flex items-center gap-3 py-2 rounded-lg text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined">memory</span>
<span class="font-label-sm text-label-sm">Memory</span>
</a>
<a class="flex items-center gap-3 py-2 rounded-lg text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined">query_stats</span>
<span class="font-label-sm text-label-sm">Benchmarks</span>
</a>
<a class="flex items-center gap-3 py-2 rounded-lg text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined">settings</span>
<span class="font-label-sm text-label-sm">Settings</span>
</a>
</div>
<div class="mt-auto border-t border-outline-variant pt-4 space-y-3">
<div class="flex items-center gap-2">
<span class="w-2 h-2 rounded-full bg-secondary glow-pulse"></span>
<span class="material-symbols-outlined text-on-surface-variant" style="font-size: 16px;">sensors</span>
<span class="font-status-dot text-status-dot text-on-surface-variant">Backend: Online</span>
</div>
<div class="flex items-center gap-2">
<span class="w-2 h-2 rounded-full bg-secondary glow-pulse"></span>
<span class="material-symbols-outlined text-on-surface-variant" style="font-size: 16px;">memory</span>
<span class="font-status-dot text-status-dot text-on-surface-variant">Ollama: Running</span>
</div>
<div class="flex items-center gap-2">
<span class="w-2 h-2 rounded-full bg-outline"></span>
<span class="material-symbols-outlined text-on-surface-variant" style="font-size: 16px;">psychology</span>
<span class="font-status-dot text-status-dot text-on-surface-variant">Cognee: Idle</span>
</div>
</div>
</nav>
<!-- Main Content Area -->
<div class="ml-sidebar-width flex-1 flex flex-col h-full bg-background relative overflow-hidden">
<!-- TopAppBar (from JSON) -->
<header class="h-16 w-full sticky top-0 z-10 bg-surface dark:bg-surface flex items-center justify-between px-gutter border-b border-outline-variant/30">
<div class="flex items-center gap-4 flex-1">
<h2 class="font-headline-sm text-headline-sm text-primary font-semibold">Context Builder</h2>
</div>
<div class="flex-1 flex justify-end">
<!-- Search placeholder if needed -->
</div>
<div class="flex items-center gap-2">
<button class="p-2 text-on-surface-variant hover:bg-surface-variant rounded-full transition-all duration-150 active:scale-95">
<span class="material-symbols-outlined">notifications</span>
</button>
<button class="p-2 text-on-surface-variant hover:bg-surface-variant rounded-full transition-all duration-150 active:scale-95">
<span class="material-symbols-outlined">account_circle</span>
</button>
</div>
</header>
<!-- Three Column Layout -->
<main class="flex-1 flex overflow-hidden p-container-margin gap-container-margin relative">
<!-- LEFT COLUMN: Input -->
<div class="w-1/3 flex flex-col bg-surface-container rounded-xl border border-outline-variant overflow-y-auto custom-scrollbar shadow-lg shadow-black/20">
<div class="p-card-padding border-b border-outline-variant bg-surface-container-high/50 sticky top-0 z-10">
<h3 class="font-headline-md text-headline-md font-medium text-on-surface flex items-center gap-2">
<span class="material-symbols-outlined text-primary">input</span>
                        Input Parameters
                    </h3>
</div>
<div class="p-card-padding flex flex-col gap-6 flex-1">
<!-- Question Input -->
<div class="space-y-2">
<label class="font-label-sm text-label-sm text-on-surface-variant">Target Objective / Question</label>
<textarea class="w-full bg-surface-container-lowest border border-outline-variant rounded-lg p-3 text-body-md font-body-md text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-none shadow-inner" placeholder="e.g., How does the authentication middleware handle token refresh in the core-api repository?" rows="4"></textarea>
</div>
<!-- Repository Selector -->
<div class="space-y-2">
<label class="font-label-sm text-label-sm text-on-surface-variant">Source Repository</label>
<div class="relative">
<select class="w-full bg-surface-container-lowest border border-outline-variant rounded-lg p-3 text-body-md font-body-md text-on-surface appearance-none focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all">
<option>andes-core-api</option>
<option>andes-web-client</option>
<option>infra-deployments</option>
</select>
<span class="material-symbols-outlined absolute right-3 top-3 text-on-surface-variant pointer-events-none">expand_more</span>
</div>
</div>
<!-- Top-K Slider -->
<div class="space-y-4">
<div class="flex justify-between items-center">
<label class="font-label-sm text-label-sm text-on-surface-variant">Retrieval Depth (Top-K)</label>
<span class="font-code-md text-code-md text-primary bg-primary/10 px-2 py-0.5 rounded">25</span>
</div>
<input class="w-full h-1 bg-outline-variant rounded-lg appearance-none cursor-pointer accent-primary" max="100" min="1" type="range" value="25"/>
</div>
<!-- Advanced Options Toggle -->
<div class="border border-outline-variant rounded-lg overflow-hidden">
<button class="w-full p-3 flex justify-between items-center bg-surface-container-high hover:bg-surface-bright transition-colors text-left" onclick="this.nextElementSibling.classList.toggle('hidden')">
<span class="font-label-sm text-label-sm text-on-surface">Advanced Options</span>
<span class="material-symbols-outlined text-on-surface-variant">tune</span>
</button>
<div class="p-3 bg-surface-container-lowest space-y-3 hidden">
<label class="flex items-center gap-3">
<input checked="" class="form-checkbox h-4 w-4 text-primary rounded border-outline-variant bg-surface-variant focus:ring-primary focus:ring-offset-surface-container-lowest" type="checkbox"/>
<span class="font-body-md text-body-md text-on-surface-variant">Semantic Deduplication</span>
</label>
<label class="flex items-center gap-3">
<input checked="" class="form-checkbox h-4 w-4 text-primary rounded border-outline-variant bg-surface-variant focus:ring-primary focus:ring-offset-surface-container-lowest" type="checkbox"/>
<span class="font-body-md text-body-md text-on-surface-variant">Resolve Cross-References</span>
</label>
<label class="flex items-center gap-3">
<input class="form-checkbox h-4 w-4 text-primary rounded border-outline-variant bg-surface-variant focus:ring-primary focus:ring-offset-surface-container-lowest" type="checkbox"/>
<span class="font-body-md text-body-md text-on-surface-variant">Aggressive Compression</span>
</label>
</div>
</div>
</div>
<div class="p-card-padding border-t border-outline-variant bg-surface-container-high/50 mt-auto">
<button class="w-full bg-primary hover:bg-primary-container text-surface-container-lowest font-label-sm text-label-sm font-semibold py-3 rounded-lg transition-all active:scale-[0.98] shadow-[0_0_15px_rgba(173,198,255,0.2)] hover:shadow-[0_0_20px_rgba(173,198,255,0.4)] flex items-center justify-center gap-2">
<span class="material-symbols-outlined">play_arrow</span>
                        Generate Context Package
                    </button>
</div>
</div>
<!-- CENTER COLUMN: Process visualization -->
<div class="w-1/3 flex flex-col gap-6">
<!-- Stats Overview -->
<div class="grid grid-cols-2 gap-4">
<div class="bg-surface-container border border-outline-variant rounded-xl p-4 flex flex-col justify-center items-center relative overflow-hidden">
<div class="absolute inset-0 bg-primary/5 opacity-50"></div>
<span class="font-label-sm text-label-sm text-on-surface-variant mb-1 z-10">Elapsed Time</span>
<span class="font-code-md text-code-md text-primary text-xl font-bold z-10">02.4s</span>
</div>
<div class="bg-surface-container border border-outline-variant rounded-xl p-4 flex flex-col justify-center items-center relative overflow-hidden">
<div class="absolute inset-0 bg-secondary/5 opacity-50"></div>
<span class="font-label-sm text-label-sm text-on-surface-variant mb-1 z-10">Est. Tokens</span>
<span class="font-code-md text-code-md text-secondary text-xl font-bold z-10">~4,250</span>
</div>
</div>
<!-- Pipeline Vis -->
<div class="flex-1 bg-surface-container rounded-xl border border-outline-variant p-card-padding flex flex-col relative overflow-y-auto custom-scrollbar shadow-lg shadow-black/20">
<h3 class="font-headline-md text-headline-md font-medium text-on-surface mb-6 flex items-center gap-2">
<span class="material-symbols-outlined text-secondary">model_training</span>
                        Processing Pipeline
                    </h3>
<div class="relative flex-1 pl-8 space-y-8">
<!-- Animated Line -->
<div class="pipeline-line"></div>
<!-- Step 1 -->
<div class="relative z-10 flex items-start gap-4">
<div class="w-8 h-8 rounded-full bg-secondary/20 border border-secondary flex items-center justify-center -ml-[30px] mt-1 flex-shrink-0">
<span class="material-symbols-outlined text-secondary text-sm">check</span>
</div>
<div>
<h4 class="font-label-sm text-label-sm text-on-surface font-semibold">Semantic Recall</h4>
<p class="font-body-md text-body-md text-on-surface-variant text-sm mt-1">Queried vector DB. Found 42 potential snippets.</p>
</div>
</div>
<!-- Step 2 -->
<div class="relative z-10 flex items-start gap-4">
<div class="w-8 h-8 rounded-full bg-secondary/20 border border-secondary flex items-center justify-center -ml-[30px] mt-1 flex-shrink-0">
<span class="material-symbols-outlined text-secondary text-sm">check</span>
</div>
<div>
<h4 class="font-label-sm text-label-sm text-on-surface font-semibold">Deduplication & Ranking</h4>
<p class="font-body-md text-body-md text-on-surface-variant text-sm mt-1">Removed 12 overlaps. Ranked top 25 by relevance.</p>
</div>
</div>
<!-- Step 3 (Active) -->
<div class="relative z-10 flex items-start gap-4">
<div class="w-8 h-8 rounded-full bg-primary/20 border-2 border-primary flex items-center justify-center -ml-[30px] mt-1 flex-shrink-0 glow-pulse">
<span class="material-symbols-outlined text-primary text-sm animate-spin">sync</span>
</div>
<div class="bg-surface-container-highest p-3 rounded-lg border border-primary/30 w-full shadow-[0_0_15px_rgba(173,198,255,0.05)]">
<h4 class="font-label-sm text-label-sm text-primary font-bold">Reference Resolution</h4>
<p class="font-body-md text-body-md text-on-surface-variant text-sm mt-1">Tracing imports and type definitions...</p>
<div class="mt-3 w-full bg-surface-container-lowest rounded-full h-1.5 overflow-hidden">
<div class="bg-primary h-1.5 rounded-full w-2/3 transition-all duration-500"></div>
</div>
</div>
</div>
<!-- Step 4 (Pending) -->
<div class="relative z-10 flex items-start gap-4 opacity-40">
<div class="w-8 h-8 rounded-full bg-surface-variant border border-outline-variant flex items-center justify-center -ml-[30px] mt-1 flex-shrink-0">
<span class="material-symbols-outlined text-on-surface-variant text-sm">compress</span>
</div>
<div>
<h4 class="font-label-sm text-label-sm text-on-surface font-semibold">Compression & Structuring</h4>
<p class="font-body-md text-body-md text-on-surface-variant text-sm mt-1">Pending...</p>
</div>
</div>
</div>
</div>
</div>
<!-- RIGHT COLUMN: Output -->
<div class="w-1/3 flex flex-col bg-surface-container rounded-xl border border-outline-variant shadow-lg shadow-black/20 flex-1 relative flex flex-col">
<!-- Toolbar -->
<div class="p-3 border-b border-outline-variant bg-surface-container-high/50 flex justify-between items-center sticky top-0 z-10">
<div class="flex gap-2">
<span class="font-label-sm text-label-sm text-on-surface px-2 py-1 bg-surface-container-lowest rounded border border-outline-variant">Markdown</span>
</div>
<div class="flex gap-2">
<button class="p-1.5 text-on-surface-variant hover:text-primary hover:bg-primary/10 rounded transition-colors" title="Copy Markdown">
<span class="material-symbols-outlined text-[20px]">content_copy</span>
</button>
<button class="p-1.5 text-on-surface-variant hover:text-secondary hover:bg-secondary/10 rounded transition-colors" title="Save Package">
<span class="material-symbols-outlined text-[20px]">save</span>
</button>
<button class="p-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-variant rounded transition-colors" title="Export">
<span class="material-symbols-outlined text-[20px]">download</span>
</button>
</div>
</div>
<!-- Markdown Content (Skeleton/Preview) -->
<div class="flex-1 p-card-padding overflow-y-auto custom-scrollbar font-code-md text-code-md text-on-surface-variant bg-[#05080f]">
<div class="opacity-70">
<span class="text-primary"># Context Package: Auth Middleware</span><br/><br/>
<span class="text-secondary">## 1. Task Objective</span><br/>
                        Understand token refresh flow in `core-api`.<br/><br/>
<span class="text-secondary">## 2. Core Components</span><br/></div></div></div></main></div></body></html>

<!-- Context Builder - AndesContext -->
<!DOCTYPE html>

<html class="dark" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>AndesContext - AI-Native Memory</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com" rel="preconnect"/>
<link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
        tailwind.config = {
          darkMode: "class",
          theme: {
            extend: {
              "colors": {
                      "outline-variant": "#424754",
                      "surface-container-lowest": "#0b0e15",
                      "on-secondary-fixed": "#002113",
                      "primary-fixed-dim": "#adc6ff",
                      "primary": "#adc6ff",
                      "secondary-fixed": "#6ffbbe",
                      "on-error-container": "#ffdad6",
                      "surface-dim": "#10131a",
                      "on-error": "#690005",
                      "secondary-fixed-dim": "#4edea3",
                      "error": "#ffb4ab",
                      "surface-variant": "#32353c",
                      "background": "#10131a",
                      "surface-bright": "#363941",
                      "on-primary": "#002e6a",
                      "primary-fixed": "#d8e2ff",
                      "on-surface": "#e1e2ec",
                      "error-container": "#93000a",
                      "surface-container-highest": "#32353c",
                      "outline": "#8c909f",
                      "tertiary-container": "#ca8100",
                      "inverse-on-surface": "#2e3038",
                      "surface-tint": "#adc6ff",
                      "on-primary-fixed-variant": "#004395",
                      "on-tertiary-container": "#3e2400",
                      "on-primary-fixed": "#001a42",
                      "secondary-container": "#00a572",
                      "primary-container": "#4d8eff",
                      "surface-container-high": "#272a31",
                      "on-tertiary-fixed": "#2a1700",
                      "on-secondary-fixed-variant": "#005236",
                      "secondary": "#4edea3",
                      "surface-container-low": "#191b23",
                      "surface": "#10131a",
                      "tertiary-fixed-dim": "#ffb95f",
                      "on-tertiary-fixed-variant": "#653e00",
                      "tertiary": "#ffb95f",
                      "tertiary-fixed": "#ffddb8",
                      "surface-container": "#1d2027",
                      "on-tertiary": "#472a00",
                      "on-secondary-container": "#00311f",
                      "on-primary-container": "#00285d",
                      "inverse-surface": "#e1e2ec",
                      "on-surface-variant": "#c2c6d6",
                      "inverse-primary": "#005ac2",
                      "on-background": "#e1e2ec",
                      "on-secondary": "#003824"
              },
              "borderRadius": {
                      "DEFAULT": "0.25rem",
                      "lg": "0.5rem",
                      "xl": "0.75rem",
                      "full": "9999px"
              },
              "spacing": {
                      "gutter": "16px",
                      "stack-gap": "12px",
                      "component-gap-sm": "8px",
                      "container-margin": "24px",
                      "card-padding": "20px",
                      "sidebar-width": "240px"
              },
              "fontFamily": {
                      "body-md": ["Inter"],
                      "label-sm": ["Inter"],
                      "status-dot": ["JetBrains Mono"],
                      "headline-md": ["Inter"],
                      "display": ["Inter"],
                      "headline-lg": ["Inter"],
                      "body-lg": ["Inter"],
                      "code-md": ["JetBrains Mono"]
              },
              "fontSize": {
                      "body-md": ["14px", {"lineHeight": "20px", "fontWeight": "400"}],
                      "label-sm": ["12px", {"lineHeight": "16px", "letterSpacing": "0.02em", "fontWeight": "500"}],
                      "status-dot": ["11px", {"lineHeight": "12px", "fontWeight": "700"}],
                      "headline-md": ["20px", {"lineHeight": "28px", "fontWeight": "500"}],
                      "display": ["32px", {"lineHeight": "40px", "letterSpacing": "-0.02em", "fontWeight": "600"}],
                      "headline-lg": ["24px", {"lineHeight": "32px", "letterSpacing": "-0.01em", "fontWeight": "600"}],
                      "body-lg": ["16px", {"lineHeight": "24px", "fontWeight": "400"}],
                      "code-md": ["13px", {"lineHeight": "20px", "fontWeight": "400"}]
              }
            }
          }
        }
    </script>
<style>
        body {
            background-color: #020617; /* Level 0 Canvas */
            color: #e1e2ec;
            margin: 0;
            overflow-x: hidden;
        }
        
        .sidebar-bg {
            background-color: #0b0e15; /* slightly darker to recede */
        }
        
        .card-bg {
            background-color: #0F172A; /* Level 1 Card */
            border: 1px solid #1E293B;
        }
        
        .card-hover:hover {
            transform: scale(1.01);
            border-color: #32353c; /* slightly brighter */
        }
        
        .btn-primary {
            background-color: #3B82F6;
            color: #FFFFFF;
        }
        
        .btn-ghost {
            background-color: transparent;
            border: 1px solid #1E293B;
        }
        .btn-ghost:hover {
            background-color: #1E293B;
        }
        
        .nav-active-pill {
            content: '';
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            width: 2px;
            height: 60%;
            background-color: #adc6ff; /* primary */
            border-radius: 0 4px 4px 0;
        }
        
        /* Ambient glows for activity */
        .glow-active {
            box-shadow: 0 0 15px rgba(173, 198, 255, 0.1);
        }

        .dot-pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
            70% { box-shadow: 0 0 0 4px rgba(59, 130, 246, 0); }
            100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
        }
        
        .timeline-line::before {
            content: '';
            position: absolute;
            left: 11px;
            top: 24px;
            bottom: -24px;
            width: 1px;
            background-color: #1E293B;
        }
        .timeline-item:last-child .timeline-line::before {
            display: none;
        }
    </style>
</head>
<body class="flex h-screen font-body-md text-on-surface antialiased overflow-hidden">
<!-- SideNavBar -->
<nav class="w-sidebar-width h-screen fixed left-0 top-0 sidebar-bg border-r border-outline-variant flex flex-col py-6 px-4 z-20">
<!-- Header -->
<div class="mb-8 px-2">
<div class="flex items-center gap-3 mb-1 text-headline-md font-headline-md font-bold tracking-tight text-on-surface">
<span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">auto_awesome</span>
<span>AndesContext</span>
</div>
<div class="text-on-surface-variant font-label-sm text-label-sm">AI-Native Memory</div>
</div>
<!-- Main Nav -->
<div class="flex-1 space-y-1">
<a class="relative flex items-center gap-3 px-3 py-2 rounded-lg text-primary font-bold border-l-2 border-primary bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">dashboard</span>
<span class="font-label-sm text-label-sm">Dashboard</span>
</a>
<a class="relative flex items-center gap-3 px-3 py-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200 pl-3" href="#">
<span class="material-symbols-outlined text-[20px]">folder_open</span>
<span class="font-label-sm text-label-sm">Repositories</span>
</a>
<a class="relative flex items-center gap-3 px-3 py-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200 pl-3" href="#">
<span class="material-symbols-outlined text-[20px]">auto_awesome_motion</span>
<span class="font-label-sm text-label-sm">Context Builder</span>
</a>
<a class="relative flex items-center gap-3 px-3 py-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200 pl-3" href="#">
<span class="material-symbols-outlined text-[20px]">memory</span>
<span class="font-label-sm text-label-sm">Memory</span>
</a>
<a class="relative flex items-center gap-3 px-3 py-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200 pl-3" href="#">
<span class="material-symbols-outlined text-[20px]">query_stats</span>
<span class="font-label-sm text-label-sm">Benchmarks</span>
</a>
<a class="relative flex items-center gap-3 px-3 py-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200 pl-3" href="#">
<span class="material-symbols-outlined text-[20px]">settings</span>
<span class="font-label-sm text-label-sm">Settings</span>
</a>
</div>
<!-- CTA -->
<div class="mt-4 mb-6">
<button class="w-full btn-primary py-2 px-4 rounded-lg font-label-sm text-label-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity">
<span class="material-symbols-outlined text-[18px]">add</span>
                New Index
            </button>
</div>
<!-- Footer / Status -->
<div class="mt-auto pt-4 border-t border-outline-variant space-y-2">
<div class="flex items-center gap-2 px-2 text-on-surface-variant">
<div class="w-2 h-2 rounded-full bg-secondary dot-pulse"></div>
<span class="font-status-dot text-status-dot">Backend: Online</span>
<span class="material-symbols-outlined ml-auto text-[14px]">sensors</span>
</div>
<div class="flex items-center gap-2 px-2 text-on-surface-variant">
<div class="w-2 h-2 rounded-full bg-secondary dot-pulse"></div>
<span class="font-status-dot text-status-dot">Ollama: Running</span>
<span class="material-symbols-outlined ml-auto text-[14px]">memory</span>
</div>
<div class="flex items-center gap-2 px-2 text-on-surface-variant">
<div class="w-2 h-2 rounded-full bg-outline"></div>
<span class="font-status-dot text-status-dot">Cognee: Idle</span>
<span class="material-symbols-outlined ml-auto text-[14px]">psychology</span>
</div>
</div>
</nav>
<!-- Main Content Area -->
<main class="flex-1 ml-sidebar-width h-screen flex flex-col overflow-y-auto">
<!-- TopAppBar -->
<header class="h-16 w-full sticky top-0 z-10 flex items-center justify-between px-gutter bg-surface backdrop-blur-md bg-opacity-90">
<div class="flex-1">
<!-- Search minimal -->
</div>
<div class="flex items-center gap-2">
<button class="text-on-surface-variant hover:bg-surface-variant rounded-full p-2 transition-all">
<span class="material-symbols-outlined">notifications</span>
</button>
<button class="text-on-surface-variant hover:bg-surface-variant rounded-full p-2 transition-all">
<span class="material-symbols-outlined">account_circle</span>
</button>
</div>
</header>
<!-- Canvas -->
<div class="px-container-margin py-8 max-w-[1440px] mx-auto w-full">
<!-- Hero Section -->
<section class="mb-12 flex flex-col gap-4">
<h1 class="font-display text-display text-on-surface tracking-tight">Build Context Packages for AI</h1>
<p class="font-body-lg text-body-lg text-on-surface-variant max-w-2xl">Transform repository knowledge into structured context for coding assistants. High-performance, local-first indexing.</p>
<div class="flex items-center gap-4 mt-2">
<button class="btn-primary px-6 py-2.5 rounded-lg font-label-sm text-label-sm font-medium flex items-center gap-2 transition-transform hover:scale-[1.02]">
<span class="material-symbols-outlined text-[18px]">download</span>
                        Import Repository
                    </button>
<button class="btn-ghost px-6 py-2.5 rounded-lg font-label-sm text-label-sm font-medium flex items-center gap-2 transition-colors">
<span class="material-symbols-outlined text-[18px]">bolt</span>
                        Generate Context
                    </button>
</div>
</section>
<!-- Grid Layout -->
<div class="grid grid-cols-1 md:grid-cols-12 gap-gutter">
<!-- Stats Bento -->
<div class="md:col-span-8 grid grid-cols-2 lg:grid-cols-3 gap-gutter">
<div class="card-bg p-card-padding rounded-xl card-hover transition-all flex flex-col justify-between h-32 glow-active">
<div class="text-on-surface-variant font-label-sm text-label-sm flex items-center gap-2">
<span class="material-symbols-outlined text-[16px] text-primary">folder_managed</span>
                            Indexed Repositories
                        </div>
<div class="font-headline-lg text-headline-lg text-on-surface">12</div>
</div>
<div class="card-bg p-card-padding rounded-xl card-hover transition-all flex flex-col justify-between h-32">
<div class="text-on-surface-variant font-label-sm text-label-sm flex items-center gap-2">
<span class="material-symbols-outlined text-[16px] text-tertiary">database</span>
                            Memories Stored
                        </div>
<div class="font-headline-lg text-headline-lg text-on-surface">1.2M</div>
</div>
<div class="card-bg p-card-padding rounded-xl card-hover transition-all flex flex-col justify-between h-32">
<div class="text-on-surface-variant font-label-sm text-label-sm flex items-center gap-2">
<span class="material-symbols-outlined text-[16px] text-secondary">inventory_2</span>
                            Packages Generated
                        </div>
<div class="font-headline-lg text-headline-lg text-on-surface">45</div>
</div>
<div class="card-bg p-card-padding rounded-xl card-hover transition-all flex flex-col justify-between h-32">
<div class="text-on-surface-variant font-label-sm text-label-sm flex items-center gap-2">
<span class="material-symbols-outlined text-[16px]">timer</span>
                            Avg. Gen Time
                        </div>
<div class="font-headline-lg text-headline-lg text-on-surface">1.4s</div>
</div>
<div class="card-bg p-card-padding rounded-xl card-hover transition-all flex flex-col justify-between h-32">
<div class="text-on-surface-variant font-label-sm text-label-sm flex items-center gap-2">
<span class="material-symbols-outlined text-[16px]">sd_card</span>
                            Avg. Package Size
                        </div>
<div class="font-headline-lg text-headline-lg text-on-surface">12KB</div>
</div>
<div class="card-bg p-card-padding rounded-xl card-hover transition-all flex flex-col justify-between h-32">
<div class="text-on-surface-variant font-label-sm text-label-sm flex items-center gap-2">
<span class="material-symbols-outlined text-[16px]">update</span>
                            Last Indexed
                        </div>
<div class="font-code-md text-code-md text-on-surface truncate px-2 py-1 bg-surface-container-lowest rounded border border-outline-variant mt-2 inline-block">
                            andes-core
                        </div>
</div>
</div>
<!-- Recent Activity Timeline -->
<div class="md:col-span-4 card-bg p-card-padding rounded-xl h-[calc(100vh-250px)] min-h-[400px] flex flex-col">
<h3 class="font-headline-md text-headline-md text-on-surface mb-6 flex items-center gap-2">
<span class="material-symbols-outlined text-[20px]">history</span>
                        Recent Activity
                    </h3>
<div class="flex-1 overflow-y-auto pr-2 space-y-6 relative">
<div class="relative flex gap-4 timeline-item">
<div class="timeline-line flex flex-col items-center">
<div class="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center z-10 border border-primary/50">
<span class="material-symbols-outlined text-[12px] text-primary">add_link</span>
</div>
</div>
<div class="flex-1 pb-4">
<p class="font-body-md text-body-md text-on-surface">Indexed <span class="font-code-md px-1 bg-surface-container-lowest rounded text-primary">andes-ui</span></p>
<p class="font-label-sm text-label-sm text-on-surface-variant mt-1">2 mins ago • 14,230 nodes added</p>
</div>
</div>
<div class="relative flex gap-4 timeline-item">
<div class="timeline-line flex flex-col items-center">
<div class="w-6 h-6 rounded-full bg-secondary/20 flex items-center justify-center z-10 border border-secondary/50">
<span class="material-symbols-outlined text-[12px] text-secondary">bolt</span>
</div>
</div>
<div class="flex-1 pb-4">
<p class="font-body-md text-body-md text-on-surface">Generated Package for 'Refactor Auth'</p>
<p class="font-label-sm text-label-sm text-on-surface-variant mt-1">15 mins ago • 45kb package</p>
</div>
</div>
<div class="relative flex gap-4 timeline-item">
<div class="timeline-line flex flex-col items-center">
<div class="w-6 h-6 rounded-full bg-surface-variant flex items-center justify-center z-10 border border-outline-variant">
<span class="material-symbols-outlined text-[12px] text-on-surface-variant">sync</span>
</div>
</div>
<div class="flex-1 pb-4">
<p class="font-body-md text-body-md text-on-surface">Background Sync Completed</p>
<p class="font-label-sm text-label-sm text-on-surface-variant mt-1">1 hour ago • No changes detected</p>
</div>
</div>
<div class="relative flex gap-4 timeline-item">
<div class="timeline-line flex flex-col items-center">
<div class="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center z-10 border border-primary/50">
<span class="material-symbols-outlined text-[12px] text-primary">add_link</span>
</div>
</div>
<div class="flex-1 pb-4">
<p class="font-body-md text-body-md text-on-surface">Indexed <span class="font-code-md px-1 bg-surface-container-lowest rounded text-primary">andes-core</span></p>
<p class="font-label-sm text-label-sm text-on-surface-variant mt-1">3 hours ago • 89,102 nodes added</p>
</div>
</div>
</div>
</div>
</div>
</div>
</main>
</body></html>

<!-- Dashboard - AndesContext -->
<!DOCTYPE html>

<html class="dark" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>AndesContext - Benchmarks</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=JetBrains+Mono:wght@400;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    "colors": {
                        "outline-variant": "#424754",
                        "surface-container-lowest": "#0b0e15",
                        "on-secondary-fixed": "#002113",
                        "primary-fixed-dim": "#adc6ff",
                        "primary": "#adc6ff",
                        "secondary-fixed": "#6ffbbe",
                        "on-error-container": "#ffdad6",
                        "surface-dim": "#10131a",
                        "on-error": "#690005",
                        "secondary-fixed-dim": "#4edea3",
                        "error": "#ffb4ab",
                        "surface-variant": "#32353c",
                        "background": "#10131a",
                        "surface-bright": "#363941",
                        "on-primary": "#002e6a",
                        "primary-fixed": "#d8e2ff",
                        "on-surface": "#e1e2ec",
                        "error-container": "#93000a",
                        "surface-container-highest": "#32353c",
                        "outline": "#8c909f",
                        "tertiary-container": "#ca8100",
                        "inverse-on-surface": "#2e3038",
                        "surface-tint": "#adc6ff",
                        "on-primary-fixed-variant": "#004395",
                        "on-tertiary-container": "#3e2400",
                        "on-primary-fixed": "#001a42",
                        "secondary-container": "#00a572",
                        "primary-container": "#4d8eff",
                        "surface-container-high": "#272a31",
                        "on-tertiary-fixed": "#2a1700",
                        "on-secondary-fixed-variant": "#005236",
                        "secondary": "#4edea3",
                        "surface-container-low": "#191b23",
                        "surface": "#10131a",
                        "tertiary-fixed-dim": "#ffb95f",
                        "on-tertiary-fixed-variant": "#653e00",
                        "tertiary": "#ffb95f",
                        "tertiary-fixed": "#ffddb8",
                        "surface-container": "#1d2027",
                        "on-tertiary": "#472a00",
                        "on-secondary-container": "#00311f",
                        "on-primary-container": "#00285d",
                        "inverse-surface": "#e1e2ec",
                        "on-surface-variant": "#c2c6d6",
                        "inverse-primary": "#005ac2",
                        "on-background": "#e1e2ec",
                        "on-secondary": "#003824"
                    },
                    "borderRadius": {
                        "DEFAULT": "0.25rem",
                        "lg": "0.5rem",
                        "xl": "0.75rem",
                        "full": "9999px"
                    },
                    "spacing": {
                        "gutter": "16px",
                        "stack-gap": "12px",
                        "component-gap-sm": "8px",
                        "container-margin": "24px",
                        "card-padding": "20px",
                        "sidebar-width": "240px"
                    },
                    "fontFamily": {
                        "body-md": ["Inter"],
                        "label-sm": ["Inter"],
                        "status-dot": ["JetBrains Mono"],
                        "headline-md": ["Inter"],
                        "display": ["Inter"],
                        "headline-lg": ["Inter"],
                        "body-lg": ["Inter"],
                        "code-md": ["JetBrains Mono"]
                    },
                    "fontSize": {
                        "body-md": ["14px", { "lineHeight": "20px", "fontWeight": "400" }],
                        "label-sm": ["12px", { "lineHeight": "16px", "letterSpacing": "0.02em", "fontWeight": "500" }],
                        "status-dot": ["11px", { "lineHeight": "12px", "fontWeight": "700" }],
                        "headline-md": ["20px", { "lineHeight": "28px", "fontWeight": "500" }],
                        "display": ["32px", { "lineHeight": "40px", "letterSpacing": "-0.02em", "fontWeight": "600" }],
                        "headline-lg": ["24px", { "lineHeight": "32px", "letterSpacing": "-0.01em", "fontWeight": "600" }],
                        "body-lg": ["16px", { "lineHeight": "24px", "fontWeight": "400" }],
                        "code-md": ["13px", { "lineHeight": "20px", "fontWeight": "400" }]
                    }
                }
            }
        }
    </script>
<style>
        .chart-grid {
            background-image: linear-gradient(to right, #32353c 1px, transparent 1px), linear-gradient(to bottom, #32353c 1px, transparent 1px);
            background-size: 40px 40px;
            opacity: 0.2;
        }
    </style>
</head>
<body class="bg-surface text-on-surface font-body-md text-body-md antialiased min-h-screen flex">
<!-- SideNavBar Component -->
<nav class="w-sidebar-width h-screen fixed left-0 top-0 bg-surface-container-low dark:bg-surface-container-lowest border-r border-outline-variant flex flex-col h-full py-6 px-4 z-20">
<!-- Header -->
<div class="flex items-center gap-3 mb-8 px-2">
<div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center border border-primary/20 shadow-[0_0_15px_rgba(173,198,255,0.1)]">
<span class="material-symbols-outlined text-primary text-[20px]" data-icon="hub">hub</span>
</div>
<div>
<h1 class="text-headline-md font-headline-md font-bold tracking-tight text-on-surface dark:text-on-surface">AndesContext</h1>
<p class="font-label-sm text-label-sm text-on-surface-variant">AI-Native Memory</p>
</div>
</div>
<!-- CTA -->
<button class="mb-6 w-full bg-primary hover:bg-primary-fixed text-on-primary font-label-sm text-label-sm py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-all active:scale-[0.99] shadow-[0_0_10px_rgba(173,198,255,0.2)]">
<span class="material-symbols-outlined text-[18px]" data-icon="add">add</span>
            New Index
        </button>
<!-- Navigation Links -->
<div class="flex flex-col gap-1 flex-1">
<!-- Dashboard (Inactive) -->
<a class="flex items-center gap-3 py-2 rounded-lg text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px] font-light" data-icon="dashboard">dashboard</span>
<span class="font-label-sm text-label-sm">Dashboard</span>
</a>
<!-- Repositories (Inactive) -->
<a class="flex items-center gap-3 py-2 rounded-lg text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px] font-light" data-icon="folder_open">folder_open</span>
<span class="font-label-sm text-label-sm">Repositories</span>
</a>
<!-- Context Builder (Inactive) -->
<a class="flex items-center gap-3 py-2 rounded-lg text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px] font-light" data-icon="auto_awesome_motion">auto_awesome_motion</span>
<span class="font-label-sm text-label-sm">Context Builder</span>
</a>
<!-- Memory (Inactive) -->
<a class="flex items-center gap-3 py-2 rounded-lg text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px] font-light" data-icon="memory">memory</span>
<span class="font-label-sm text-label-sm">Memory</span>
</a>
<!-- Benchmarks (ACTIVE) -->
<a class="flex items-center gap-3 py-2 rounded-lg text-primary dark:text-primary font-bold border-l-2 border-primary pl-3 bg-primary/5 active:opacity-90 transition-all scale-[0.99] shadow-[inset_2px_0_0_0_var(--tw-colors-primary)]" href="#">
<span class="material-symbols-outlined text-[20px] font-normal" data-icon="query_stats" data-weight="fill" style="font-variation-settings: 'FILL' 1;">query_stats</span>
<span class="font-label-sm text-label-sm">Benchmarks</span>
</a>
<!-- Settings (Inactive) -->
<a class="flex items-center gap-3 py-2 rounded-lg text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface pl-3 hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px] font-light" data-icon="settings">settings</span>
<span class="font-label-sm text-label-sm">Settings</span>
</a>
</div>
<!-- Footer Status -->
<div class="mt-auto pt-4 border-t border-outline-variant/30 flex flex-col gap-2">
<div class="flex items-center gap-2 px-2">
<span class="material-symbols-outlined text-[16px] text-secondary" data-icon="sensors">sensors</span>
<span class="font-status-dot text-status-dot text-on-surface-variant uppercase tracking-wider">Backend: Online</span>
<div class="w-1.5 h-1.5 rounded-full bg-secondary ml-auto shadow-[0_0_8px_rgba(78,222,163,0.6)]"></div>
</div>
<div class="flex items-center gap-2 px-2">
<span class="material-symbols-outlined text-[16px] text-primary" data-icon="memory">memory</span>
<span class="font-status-dot text-status-dot text-on-surface-variant uppercase tracking-wider">Ollama: Running</span>
<div class="w-1.5 h-1.5 rounded-full bg-primary ml-auto shadow-[0_0_8px_rgba(173,198,255,0.6)] animate-pulse"></div>
</div>
<div class="flex items-center gap-2 px-2">
<span class="material-symbols-outlined text-[16px] text-outline" data-icon="psychology">psychology</span>
<span class="font-status-dot text-status-dot text-outline uppercase tracking-wider">Cognee: Idle</span>
<div class="w-1.5 h-1.5 rounded-full bg-outline ml-auto"></div>
</div>
</div>
</nav>
<!-- Main Content Wrapper -->
<div class="ml-sidebar-width w-full flex flex-col min-h-screen">
<!-- TopAppBar Component -->
<header class="h-16 w-full sticky top-0 z-10 bg-surface dark:bg-surface flex items-center justify-between px-gutter">
<div class="flex-1"></div> <!-- Spacer for layout -->
<div class="flex items-center gap-2">
<button class="text-on-surface-variant hover:bg-surface-variant rounded-full p-2 transition-all active:scale-95 duration-150 flex items-center justify-center">
<span class="material-symbols-outlined" data-icon="notifications">notifications</span>
</button>
<button class="text-on-surface-variant hover:bg-surface-variant rounded-full p-2 transition-all active:scale-95 duration-150 flex items-center justify-center">
<span class="material-symbols-outlined" data-icon="account_circle">account_circle</span>
</button>
</div>
</header>
<!-- Main Dashboard Canvas -->
<main class="flex-1 p-container-margin flex flex-col gap-container-margin max-w-[1440px] w-full mx-auto">
<!-- Page Header -->
<div class="flex items-end justify-between border-b border-surface-variant pb-4">
<div>
<h2 class="font-display text-display text-on-surface mb-1">Performance Benchmarks</h2>
<p class="font-body-lg text-body-lg text-on-surface-variant">Real-time telemetry and comparative analysis for AndesContext engine.</p>
</div>
<div class="flex items-center gap-3">
<button class="flex items-center gap-2 px-3 py-1.5 rounded-md border border-outline-variant bg-transparent text-label-sm font-label-sm text-on-surface hover:bg-surface-container-high transition-colors">
<span class="material-symbols-outlined text-[16px]" data-icon="calendar_today">calendar_today</span>
                        Last 7 Days
                        <span class="material-symbols-outlined text-[16px]" data-icon="arrow_drop_down">arrow_drop_down</span>
</button>
<button class="flex items-center gap-2 px-3 py-1.5 rounded-md bg-primary text-on-primary text-label-sm font-label-sm hover:bg-primary-fixed transition-colors shadow-[0_0_10px_rgba(173,198,255,0.15)]">
<span class="material-symbols-outlined text-[16px]" data-icon="refresh">refresh</span>
                        Run Suite
                    </button>
</div>
</div>
<!-- Bento Grid - Top Metrics -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-stack-gap">
<!-- Metric 1: Quality Score (Gauge) -->
<div class="bg-surface-container-low border border-outline-variant/50 rounded-xl p-card-padding relative overflow-hidden group hover:border-outline-variant transition-colors hover:scale-[1.01] duration-200">
<div class="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
<div class="flex justify-between items-start mb-4">
<h3 class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide">Avg Quality Score</h3>
<span class="material-symbols-outlined text-primary text-[20px]" data-icon="verified">verified</span>
</div>
<div class="flex items-end gap-3">
<span class="font-display text-display text-on-surface leading-none">94.2</span>
<span class="font-status-dot text-status-dot text-secondary flex items-center gap-0.5 mb-1">
<span class="material-symbols-outlined text-[12px]" data-icon="trending_up">trending_up</span> +2.4
                        </span>
</div>
<!-- CSS Gauge Representation -->
<div class="mt-6 relative h-2 bg-surface-variant rounded-full overflow-hidden">
<div class="absolute top-0 left-0 h-full bg-primary rounded-full" style="width: 94.2%;"></div>
<div class="absolute top-0 left-0 h-full w-full bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] animate-[shimmer_2s_infinite]"></div>
</div>
</div>
<!-- Metric 2: Generation Latency -->
<div class="bg-surface-container-low border border-outline-variant/50 rounded-xl p-card-padding hover:border-outline-variant transition-colors hover:scale-[1.01] duration-200">
<div class="flex justify-between items-start mb-4">
<h3 class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide">Gen Latency (p95)</h3>
<span class="material-symbols-outlined text-on-surface-variant text-[20px]" data-icon="timer">timer</span>
</div>
<div class="flex items-end gap-3">
<span class="font-display text-display text-on-surface leading-none">245<span class="text-headline-md text-on-surface-variant">ms</span></span>
<span class="font-status-dot text-status-dot text-secondary flex items-center gap-0.5 mb-1">
<span class="material-symbols-outlined text-[12px]" data-icon="trending_down">trending_down</span> -12ms
                        </span>
</div>
<!-- Sparkline Mock -->
<div class="mt-4 h-8 flex items-end gap-1 opacity-70">
<div class="w-full bg-primary/20 h-[40%] rounded-t-sm"></div>
<div class="w-full bg-primary/20 h-[50%] rounded-t-sm"></div>
<div class="w-full bg-primary/20 h-[30%] rounded-t-sm"></div>
<div class="w-full bg-primary/20 h-[60%] rounded-t-sm"></div>
<div class="w-full bg-primary/20 h-[45%] rounded-t-sm"></div>
<div class="w-full bg-primary/40 h-[35%] rounded-t-sm"></div>
<div class="w-full bg-primary/60 h-[25%] rounded-t-sm"></div>
</div>
</div>
<!-- Metric 3: Hallucination Rate -->
<div class="bg-surface-container-low border border-outline-variant/50 rounded-xl p-card-padding hover:border-outline-variant transition-colors hover:scale-[1.01] duration-200">
<div class="flex justify-between items-start mb-4">
<h3 class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide">Hallucination Rate</h3>
<span class="material-symbols-outlined text-secondary text-[20px]" data-icon="rule">rule</span>
</div>
<div class="flex items-end gap-3">
<span class="font-display text-display text-on-surface leading-none">0.8<span class="text-headline-md text-on-surface-variant">%</span></span>
<span class="font-status-dot text-status-dot text-on-surface-variant flex items-center gap-0.5 mb-1">
                             stable
                        </span>
</div>
<!-- Progress Bar Mock -->
<div class="mt-6 h-1 flex gap-0.5">
<div class="flex-1 bg-secondary rounded-l-full"></div>
<div class="flex-1 bg-secondary"></div>
<div class="flex-1 bg-secondary"></div>
<div class="flex-1 bg-secondary"></div>
<div class="flex-1 bg-surface-variant rounded-r-full"></div>
</div>
</div>
<!-- Metric 4: Context Coverage -->
<div class="bg-surface-container-low border border-outline-variant/50 rounded-xl p-card-padding hover:border-outline-variant transition-colors hover:scale-[1.01] duration-200">
<div class="flex justify-between items-start mb-4">
<h3 class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wide">Context Coverage</h3>
<span class="material-symbols-outlined text-on-surface-variant text-[20px]" data-icon="data_usage">data_usage</span>
</div>
<div class="flex items-end gap-3">
<span class="font-display text-display text-on-surface leading-none">88.5<span class="text-headline-md text-on-surface-variant">%</span></span>
<span class="font-status-dot text-status-dot text-secondary flex items-center gap-0.5 mb-1">
<span class="material-symbols-outlined text-[12px]" data-icon="trending_up">trending_up</span> +5.1%
                        </span>
</div>
<div class="mt-6 flex justify-between font-code-md text-code-md text-outline">
<span>Min: 72%</span>
<span>Max: 99%</span>
</div>
</div>
</div>
<!-- Charts Section -->
<div class="grid grid-cols-1 lg:grid-cols-3 gap-stack-gap h-[400px]">
<!-- Line Chart: Latency over Time (Takes 2 columns) -->
<div class="lg:col-span-2 bg-surface-container-low border border-outline-variant/50 rounded-xl p-card-padding flex flex-col relative overflow-hidden">
<div class="flex justify-between items-center mb-6">
<div>
<h3 class="font-headline-sm text-headline-sm text-on-surface">Generation Latency</h3>
<p class="font-label-sm text-label-sm text-on-surface-variant mt-1">Rolling average over last 24 hours.</p>
</div>
<div class="flex gap-4">
<div class="flex items-center gap-2">
<div class="w-3 h-0.5 bg-primary rounded-full"></div>
<span class="font-label-sm text-label-sm text-on-surface-variant">AndesContext</span>
</div>
<div class="flex items-center gap-2">
<div class="w-3 h-0.5 bg-outline rounded-full"></div>
<span class="font-label-sm text-label-sm text-on-surface-variant">Raw Model</span>
</div>
</div>
</div>
<!-- Visual Chart Mockup (SVG) -->
<div class="flex-1 relative chart-grid border-l border-b border-surface-variant mt-2 mx-4 mb-4">
<!-- Y Axis Labels -->
<div class="absolute -left-10 top-0 h-full flex flex-col justify-between text-[10px] text-outline font-code-md py-1">
<span>800ms</span>
<span>600ms</span>
<span>400ms</span>
<span>200ms</span>
<span>0ms</span>
</div>
<!-- X Axis Labels -->
<div class="absolute -bottom-6 left-0 w-full flex justify-between text-[10px] text-outline font-code-md px-1">
<span>00:00</span>
<span>06:00</span>
<span>12:00</span>
<span>18:00</span>
<span>Now</span>
</div>
<svg class="absolute inset-0 w-full h-full overflow-visible" preserveaspectratio="none" viewbox="0 0 100 100">
<!-- Raw Model Line (Muted) -->
<path d="M 0,40 Q 10,45 20,30 T 40,50 T 60,35 T 80,45 T 100,20" fill="none" stroke="#424754" stroke-dasharray="4 2" stroke-width="1.5"></path>
<!-- AndesContext Line (Primary) -->
<path class="drop-shadow-[0_4px_6px_rgba(173,198,255,0.2)]" d="M 0,70 Q 15,65 30,75 T 50,60 T 70,80 T 90,65 T 100,75" fill="none" stroke="#adc6ff" stroke-width="2"></path>
<!-- Gradient Area under Primary Line -->
<path d="M 0,70 Q 15,65 30,75 T 50,60 T 70,80 T 90,65 T 100,75 L 100,100 L 0,100 Z" fill="url(#primary-gradient)" opacity="0.1"></path>
<defs>
<lineargradient id="primary-gradient" x1="0%" x2="0%" y1="0%" y2="100%">
<stop offset="0%" stop-color="#adc6ff"></stop>
<stop offset="100%" stop-color="transparent"></stop>
</lineargradient>
</defs>
<!-- Data Point Marker -->
<circle class="animate-pulse" cx="100" cy="75" fill="#adc6ff" r="3"></circle>
</svg>
</div>
</div>
<!-- Bar Chart: Raw vs AndesContext -->
<div class="bg-surface-container-low border border-outline-variant/50 rounded-xl p-card-padding flex flex-col">
<div class="mb-6">
<h3 class="font-headline-sm text-headline-sm text-on-surface">Throughput Compare</h3>
<p class="font-label-sm text-label-sm text-on-surface-variant mt-1">Tokens per second (avg).</p>
</div>
<div class="flex-1 flex items-end justify-around pb-4 border-b border-surface-variant chart-grid px-4">
<!-- Group 1 -->
<div class="flex flex-col items-center gap-2 group w-1/4">
<span class="font-code-md text-code-md text-on-surface opacity-0 group-hover:opacity-100 transition-opacity absolute -mt-6">24</span>
<div class="w-full bg-surface-variant rounded-t-sm h-[30%] hover:brightness-110 transition-all"></div>
<span class="text-[10px] text-outline font-code-md mt-2">Raw</span>
</div>
<div class="flex flex-col items-center gap-2 group w-1/4">
<span class="font-code-md text-code-md text-primary opacity-0 group-hover:opacity-100 transition-opacity absolute -mt-6 shadow-[0_0_8px_rgba(173,198,255,0.3)]">68</span>
<div class="w-full bg-primary rounded-t-sm h-[85%] shadow-[0_0_10px_rgba(173,198,255,0.1)] hover:brightness-110 transition-all"></div>
<span class="text-[10px] text-primary font-code-md mt-2">Andes</span>
</div>
</div>
<div class="mt-4 flex justify-center gap-4">
<div class="flex items-center gap-2">
<div class="w-2 h-2 bg-surface-variant rounded-sm"></div>
<span class="font-label-sm text-label-sm text-on-surface-variant">Cognee Default</span>
</div>
<div class="flex items-center gap-2">
<div class="w-2 h-2 bg-primary rounded-sm"></div>
<span class="font-label-sm text-label-sm text-on-surface-variant">AndesContext</span>
</div>
</div>
</div>
</div>
</main>
</div>
<style>
        @keyframes shimmer {
            100% {
                transform: translateX(100%);
            }
        }
    </style>
</body></html>

<!-- Benchmarks - AndesContext -->
<!DOCTYPE html>

<html class="dark" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>AndesContext - Settings</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<script id="tailwind-config">
      tailwind.config = {
        darkMode: "class",
        theme: {
          extend: {
            "colors": {
                    "outline-variant": "#424754",
                    "surface-container-lowest": "#0b0e15",
                    "on-secondary-fixed": "#002113",
                    "primary-fixed-dim": "#adc6ff",
                    "primary": "#adc6ff",
                    "secondary-fixed": "#6ffbbe",
                    "on-error-container": "#ffdad6",
                    "surface-dim": "#10131a",
                    "on-error": "#690005",
                    "secondary-fixed-dim": "#4edea3",
                    "error": "#ffb4ab",
                    "surface-variant": "#32353c",
                    "background": "#10131a",
                    "surface-bright": "#363941",
                    "on-primary": "#002e6a",
                    "primary-fixed": "#d8e2ff",
                    "on-surface": "#e1e2ec",
                    "error-container": "#93000a",
                    "surface-container-highest": "#32353c",
                    "outline": "#8c909f",
                    "tertiary-container": "#ca8100",
                    "inverse-on-surface": "#2e3038",
                    "surface-tint": "#adc6ff",
                    "on-primary-fixed-variant": "#004395",
                    "on-tertiary-container": "#3e2400",
                    "on-primary-fixed": "#001a42",
                    "secondary-container": "#00a572",
                    "primary-container": "#4d8eff",
                    "surface-container-high": "#272a31",
                    "on-tertiary-fixed": "#2a1700",
                    "on-secondary-fixed-variant": "#005236",
                    "secondary": "#4edea3",
                    "surface-container-low": "#191b23",
                    "surface": "#10131a",
                    "tertiary-fixed-dim": "#ffb95f",
                    "on-tertiary-fixed-variant": "#653e00",
                    "tertiary": "#ffb95f",
                    "tertiary-fixed": "#ffddb8",
                    "surface-container": "#1d2027",
                    "on-tertiary": "#472a00",
                    "on-secondary-container": "#00311f",
                    "on-primary-container": "#00285d",
                    "inverse-surface": "#e1e2ec",
                    "on-surface-variant": "#c2c6d6",
                    "inverse-primary": "#005ac2",
                    "on-background": "#e1e2ec",
                    "on-secondary": "#003824"
            },
            "borderRadius": {
                    "DEFAULT": "0.25rem",
                    "lg": "0.5rem",
                    "xl": "0.75rem",
                    "full": "9999px"
            },
            "spacing": {
                    "gutter": "16px",
                    "stack-gap": "12px",
                    "component-gap-sm": "8px",
                    "container-margin": "24px",
                    "card-padding": "20px",
                    "sidebar-width": "240px"
            },
            "fontFamily": {
                    "body-md": ["Inter"],
                    "label-sm": ["Inter"],
                    "status-dot": ["JetBrains Mono"],
                    "headline-md": ["Inter"],
                    "display": ["Inter"],
                    "headline-lg": ["Inter"],
                    "body-lg": ["Inter"],
                    "code-md": ["JetBrains Mono"]
            },
            "fontSize": {
                    "body-md": ["14px", {"lineHeight": "20px", "fontWeight": "400"}],
                    "label-sm": ["12px", {"lineHeight": "16px", "letterSpacing": "0.02em", "fontWeight": "500"}],
                    "status-dot": ["11px", {"lineHeight": "12px", "fontWeight": "700"}],
                    "headline-md": ["20px", {"lineHeight": "28px", "fontWeight": "500"}],
                    "display": ["32px", {"lineHeight": "40px", "letterSpacing": "-0.02em", "fontWeight": "600"}],
                    "headline-lg": ["24px", {"lineHeight": "32px", "letterSpacing": "-0.01em", "fontWeight": "600"}],
                    "body-lg": ["16px", {"lineHeight": "24px", "fontWeight": "400"}],
                    "code-md": ["13px", {"lineHeight": "20px", "fontWeight": "400"}]
            }
          }
        }
      }
    </script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<style>
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 20;
        }
        /* Custom scrollbar for webkit */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #32353c; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #424754; }
        
        /* Smooth transitions for tabs */
        .tab-content { display: none; animation: fadeIn 0.2s ease-out; }
        .tab-content.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body class="bg-background text-on-surface font-body-md h-screen flex overflow-hidden antialiased selection:bg-primary-container selection:text-on-primary-container">
<!-- Shared Component: SideNavBar -->
<nav class="w-sidebar-width h-screen fixed left-0 top-0 bg-surface-container-low border-r border-outline-variant flex flex-col h-full py-6 px-4 z-20">
<!-- Header -->
<div class="flex items-center gap-3 mb-8 px-2">
<div class="w-8 h-8 rounded bg-primary/10 flex items-center justify-center border border-primary/20">
<span class="material-symbols-outlined text-primary text-[20px]" data-weight="fill" style="font-variation-settings: 'FILL' 1;">auto_awesome</span>
</div>
<div>
<h1 class="text-headline-md font-headline-md font-bold tracking-tight text-on-surface">AndesContext</h1>
<p class="font-label-sm text-label-sm text-on-surface-variant">AI-Native Memory</p>
</div>
</div>
<!-- Primary Tabs -->
<div class="flex-1 space-y-1">
<a class="flex items-center gap-3 py-2 px-3 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">dashboard</span>
<span class="font-body-md text-body-md">Dashboard</span>
</a>
<a class="flex items-center gap-3 py-2 px-3 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">folder_open</span>
<span class="font-body-md text-body-md">Repositories</span>
</a>
<a class="flex items-center gap-3 py-2 px-3 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">auto_awesome_motion</span>
<span class="font-body-md text-body-md">Context Builder</span>
</a>
<a class="flex items-center gap-3 py-2 px-3 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">memory</span>
<span class="font-body-md text-body-md">Memory</span>
</a>
<a class="flex items-center gap-3 py-2 px-3 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200" href="#">
<span class="material-symbols-outlined text-[20px]">query_stats</span>
<span class="font-body-md text-body-md">Benchmarks</span>
</a>
<!-- Active Tab -->
<a class="flex items-center gap-3 py-2 px-3 rounded-md bg-surface-container-high text-primary font-bold border-l-2 border-primary transition-colors duration-200 opacity-90 scale-[0.99]" href="#">
<span class="material-symbols-outlined text-[20px]" style="font-variation-settings: 'FILL' 1;">settings</span>
<span class="font-body-md text-body-md">Settings</span>
</a>
</div>
<!-- CTA -->
<div class="mt-6 mb-6">
<button class="w-full py-2 px-4 rounded-md bg-primary text-on-primary font-label-sm text-label-sm font-semibold hover:bg-primary-fixed transition-colors flex items-center justify-center gap-2">
<span class="material-symbols-outlined text-[18px]">add</span>
                New Index
            </button>
</div>
<!-- Footer / Status -->
<div class="border-t border-outline-variant pt-4 space-y-3">
<div class="flex items-center gap-2 px-2">
<div class="w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_rgba(78,222,163,0.5)]"></div>
<span class="material-symbols-outlined text-[16px] text-on-surface-variant">sensors</span>
<span class="font-status-dot text-status-dot text-on-surface-variant">Backend: Online</span>
</div>
<div class="flex items-center gap-2 px-2">
<div class="w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_rgba(78,222,163,0.5)]"></div>
<span class="material-symbols-outlined text-[16px] text-on-surface-variant">memory</span>
<span class="font-status-dot text-status-dot text-on-surface-variant">Ollama: Running</span>
</div>
<div class="flex items-center gap-2 px-2">
<div class="w-2 h-2 rounded-full bg-outline-variant"></div>
<span class="material-symbols-outlined text-[16px] text-outline">psychology</span>
<span class="font-status-dot text-status-dot text-outline">Cognee: Idle</span>
</div>
</div>
</nav>
<!-- Main Content Area -->
<main class="flex-1 ml-[240px] flex bg-background h-full overflow-hidden">
<!-- Settings Secondary Nav -->
<div class="w-[220px] h-full border-r border-outline-variant bg-surface/50 flex flex-col py-8 px-4 overflow-y-auto">
<h2 class="font-label-sm text-label-sm text-outline uppercase tracking-wider mb-4 px-2">Configuration</h2>
<nav class="space-y-1" id="settings-nav">
<button class="w-full flex items-center justify-between py-2 px-3 rounded-md text-left text-on-surface bg-surface-container-high transition-colors font-body-md text-body-md" data-target="backend">
                    Backend
                </button>
<button class="w-full flex items-center justify-between py-2 px-3 rounded-md text-left text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors font-body-md text-body-md" data-target="cognee">
                    Cognee
                </button>
<button class="w-full flex items-center justify-between py-2 px-3 rounded-md text-left text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors font-body-md text-body-md" data-target="ollama">
                    Ollama
                </button>
<button class="w-full flex items-center justify-between py-2 px-3 rounded-md text-left text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors font-body-md text-body-md" data-target="storage">
                    Storage
                </button>
<h2 class="font-label-sm text-label-sm text-outline uppercase tracking-wider mt-8 mb-4 px-2">Application</h2>
<button class="w-full flex items-center justify-between py-2 px-3 rounded-md text-left text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors font-body-md text-body-md" data-target="theme">
                    Theme
                </button>
<button class="w-full flex items-center justify-between py-2 px-3 rounded-md text-left text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors font-body-md text-body-md" data-target="about">
                    About
                </button>
</nav>
</div>
<!-- Settings Content Canvas -->
<div class="flex-1 h-full overflow-y-auto p-8 lg:p-12">
<div class="max-w-3xl mx-auto">
<!-- Backend Settings -->
<div class="tab-content active space-y-8" id="backend">
<div>
<h2 class="font-headline-lg text-headline-lg text-on-surface mb-2">Backend Configuration</h2>
<p class="font-body-md text-body-md text-on-surface-variant">Manage connection details for the primary AndesContext orchestration server.</p>
</div>
<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-card-padding shadow-sm">
<div class="space-y-6">
<!-- Field group -->
<div class="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
<div class="md:w-1/3">
<label class="font-label-sm text-label-sm text-on-surface block">Host URL</label>
<span class="font-body-md text-body-md text-outline text-xs mt-1 block">The address of your backend instance.</span>
</div>
<div class="md:w-2/3">
<input class="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-code-md text-code-md transition-colors placeholder-outline" type="text" value="http://127.0.0.1"/>
</div>
</div>
<div class="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
<div class="md:w-1/3">
<label class="font-label-sm text-label-sm text-on-surface block">Port</label>
</div>
<div class="md:w-2/3">
<input class="w-full max-w-[150px] bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-code-md text-code-md transition-colors" type="number" value="8000"/>
</div>
</div>
<div class="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
<div class="md:w-1/3">
<label class="font-label-sm text-label-sm text-on-surface block">API Key</label>
<span class="font-body-md text-body-md text-outline text-xs mt-1 block">Required if authentication is enabled on the server.</span>
</div>
<div class="md:w-2/3 relative">
<input class="w-full bg-surface-container h-10 pl-3 pr-10 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-code-md text-code-md transition-colors" type="password" value="sk-andes-local-dev-12345"/>
<button class="absolute right-3 top-2.5 text-outline hover:text-on-surface transition-colors">
<span class="material-symbols-outlined text-[20px]">visibility</span>
</button>
</div>
</div>
</div>
</div>
<div class="flex justify-end">
<button class="px-4 py-2 bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20 rounded-md font-label-sm text-label-sm transition-colors">Test Connection</button>
</div>
</div>
<!-- Cognee Settings -->
<div class="tab-content space-y-8" id="cognee">
<div>
<h2 class="font-headline-lg text-headline-lg text-on-surface mb-2">Cognee Integration</h2>
<p class="font-body-md text-body-md text-on-surface-variant">Configure vector database and knowledge graph processing pipelines.</p>
</div>
<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-card-padding shadow-sm">
<div class="space-y-6">
<div class="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
<div class="md:w-1/3">
<label class="font-label-sm text-label-sm text-on-surface block">Vector Database</label>
</div>
<div class="md:w-2/3">
<select class="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-body-md text-body-md transition-colors appearance-none">
<option selected="" value="qdrant">Qdrant (Local)</option>
<option value="milvus">Milvus</option>
<option value="weaviate">Weaviate</option>
</select>
</div>
</div>
<div class="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
<div class="md:w-1/3">
<label class="font-label-sm text-label-sm text-on-surface block">Graph Features</label>
</div>
<div class="md:w-2/3 space-y-4">
<label class="flex items-center gap-3 cursor-pointer group">
<div class="relative flex items-center justify-center w-5 h-5 rounded border border-primary bg-primary/20">
<span class="material-symbols-outlined text-[14px] text-primary">check</span>
</div>
<span class="font-body-md text-body-md text-on-surface group-hover:text-primary transition-colors">Enable Knowledge Graph extraction</span>
</label>
<label class="flex items-center gap-3 cursor-pointer group">
<div class="relative flex items-center justify-center w-5 h-5 rounded border border-outline-variant bg-surface-container">
</div>
<span class="font-body-md text-body-md text-on-surface group-hover:text-primary transition-colors">Auto-link detected entities</span>
</label>
</div>
</div>
</div>
</div>
</div>
<!-- Ollama Settings -->
<div class="tab-content space-y-8" id="ollama">
<div>
<h2 class="font-headline-lg text-headline-lg text-on-surface mb-2">Ollama Configuration</h2>
<p class="font-body-md text-body-md text-on-surface-variant">Set up your local inference engine and default models.</p>
</div>
<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-card-padding shadow-sm">
<div class="space-y-6">
<div class="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
<div class="md:w-1/3">
<label class="font-label-sm text-label-sm text-on-surface block">Local Endpoint</label>
</div>
<div class="md:w-2/3">
<input class="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-code-md text-code-md transition-colors" type="text" value="http://127.0.0.1:11434"/>
</div>
</div>
<div class="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
<div class="md:w-1/3">
<label class="font-label-sm text-label-sm text-on-surface block">Default Model</label>
<span class="font-body-md text-body-md text-outline text-xs mt-1 block">Used for embeddings and basic inference if not specified in request.</span>
</div>
<div class="md:w-2/3">
<select class="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-body-md text-body-md transition-colors appearance-none">
<option value="llama3">llama3:8b</option>
<option selected="" value="mistral">mistral:instruct</option>
<option value="nomic-embed-text">nomic-embed-text</option>
</select>
</div>
</div>
</div>
</div>
</div>
<!-- (Placeholder for Storage, Theme, About for brevity, following same pattern) -->
<div class="tab-content space-y-8" id="storage">
<div>
<h2 class="font-headline-lg text-headline-lg text-on-surface mb-2">Storage &amp; Cache</h2>
<p class="font-body-md text-body-md text-on-surface-variant">Manage where AndesContext stores local data.</p>
</div>
<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-card-padding shadow-sm">
<div class="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
<div class="md:w-1/3">
<label class="font-label-sm text-label-sm text-on-surface block">Persistent Path</label>
</div>
<div class="md:w-2/3 flex gap-2">
<input class="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant text-outline font-code-md text-code-md cursor-not-allowed" readonly="" type="text" value="~/.andes/data"/>
<button class="px-3 h-10 bg-surface-container hover:bg-surface-bright border border-outline-variant rounded-md text-on-surface transition-colors">
<span class="material-symbols-outlined text-[20px]">folder</span>
</button>
</div>
</div>
</div>
</div>
</div>
</div>
</main>
<script>
        // Simple tab switching logic
        const navButtons = document.querySelectorAll('#settings-nav button');
        const tabContents = document.querySelectorAll('.tab-content');

        navButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                // Update nav styling
                navButtons.forEach(b => {
                    b.classList.remove('bg-surface-container-high', 'text-on-surface');
                    b.classList.add('text-on-surface-variant');
                });
                btn.classList.add('bg-surface-container-high', 'text-on-surface');
                btn.classList.remove('text-on-surface-variant');

                // Switch content
                const targetId = btn.getAttribute('data-target');
                tabContents.forEach(content => {
                    if(content.id === targetId) {
                        content.classList.add('active');
                    } else {
                        content.classList.remove('active');
                    }
                });
            });
        });
    </script>
</body></html>

<!-- Settings - AndesContext -->
<!DOCTYPE html>

<html class="dark" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>AndesContext - Memory</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=JetBrains+Mono:wght@400;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
        tailwind.config = {
          darkMode: "class",
          theme: {
            extend: {
              "colors": {
                      "outline-variant": "#424754",
                      "surface-container-lowest": "#0b0e15",
                      "on-secondary-fixed": "#002113",
                      "primary-fixed-dim": "#adc6ff",
                      "primary": "#adc6ff",
                      "secondary-fixed": "#6ffbbe",
                      "on-error-container": "#ffdad6",
                      "surface-dim": "#10131a",
                      "on-error": "#690005",
                      "secondary-fixed-dim": "#4edea3",
                      "error": "#ffb4ab",
                      "surface-variant": "#32353c",
                      "background": "#10131a",
                      "surface-bright": "#363941",
                      "on-primary": "#002e6a",
                      "primary-fixed": "#d8e2ff",
                      "on-surface": "#e1e2ec",
                      "error-container": "#93000a",
                      "surface-container-highest": "#32353c",
                      "outline": "#8c909f",
                      "tertiary-container": "#ca8100",
                      "inverse-on-surface": "#2e3038",
                      "surface-tint": "#adc6ff",
                      "on-primary-fixed-variant": "#004395",
                      "on-tertiary-container": "#3e2400",
                      "on-primary-fixed": "#001a42",
                      "secondary-container": "#00a572",
                      "primary-container": "#4d8eff",
                      "surface-container-high": "#272a31",
                      "on-tertiary-fixed": "#2a1700",
                      "on-secondary-fixed-variant": "#005236",
                      "secondary": "#4edea3",
                      "surface-container-low": "#191b23",
                      "surface": "#10131a",
                      "tertiary-fixed-dim": "#ffb95f",
                      "on-tertiary-fixed-variant": "#653e00",
                      "tertiary": "#ffb95f",
                      "tertiary-fixed": "#ffddb8",
                      "surface-container": "#1d2027",
                      "on-tertiary": "#472a00",
                      "on-secondary-container": "#00311f",
                      "on-primary-container": "#00285d",
                      "inverse-surface": "#e1e2ec",
                      "on-surface-variant": "#c2c6d6",
                      "inverse-primary": "#005ac2",
                      "on-background": "#e1e2ec",
                      "on-secondary": "#003824"
              },
              "borderRadius": {
                      "DEFAULT": "0.25rem",
                      "lg": "0.5rem",
                      "xl": "0.75rem",
                      "full": "9999px"
              },
              "spacing": {
                      "gutter": "16px",
                      "stack-gap": "12px",
                      "component-gap-sm": "8px",
                      "container-margin": "24px",
                      "card-padding": "20px",
                      "sidebar-width": "240px"
              },
              "fontFamily": {
                      "body-md": [
                              "Inter"
                      ],
                      "label-sm": [
                              "Inter"
                      ],
                      "status-dot": [
                              "JetBrains Mono"
                      ],
                      "headline-md": [
                              "Inter"
                      ],
                      "display": [
                              "Inter"
                      ],
                      "headline-lg": [
                              "Inter"
                      ],
                      "body-lg": [
                              "Inter"
                      ],
                      "code-md": [
                              "JetBrains Mono"
                      ]
              },
              "fontSize": {
                      "body-md": [
                              "14px",
                              {
                                      "lineHeight": "20px",
                                      "fontWeight": "400"
                              }
                      ],
                      "label-sm": [
                              "12px",
                              {
                                      "lineHeight": "16px",
                                      "letterSpacing": "0.02em",
                                      "fontWeight": "500"
                              }
                      ],
                      "status-dot": [
                              "11px",
                              {
                                      "lineHeight": "12px",
                                      "fontWeight": "700"
                              }
                      ],
                      "headline-md": [
                              "20px",
                              {
                                      "lineHeight": "28px",
                                      "fontWeight": "500"
                              }
                      ],
                      "display": [
                              "32px",
                              {
                                      "lineHeight": "40px",
                                      "letterSpacing": "-0.02em",
                                      "fontWeight": "600"
                              }
                      ],
                      "headline-lg": [
                              "24px",
                              {
                                      "lineHeight": "32px",
                                      "letterSpacing": "-0.01em",
                                      "fontWeight": "600"
                              }
                      ],
                      "body-lg": [
                              "16px",
                              {
                                      "lineHeight": "24px",
                                      "fontWeight": "400"
                              }
                      ],
                      "code-md": [
                              "13px",
                              {
                                      "lineHeight": "20px",
                                      "fontWeight": "400"
                              }
                      ]
              }
      },
          },
        }
      </script>
</head>
<body class="bg-[#020617] text-on-surface font-body-md min-h-screen flex">
<!-- SideNavBar Component -->
<nav class="w-sidebar-width h-screen fixed left-0 top-0 bg-surface-container-low dark:bg-surface-container-lowest border-r border-outline-variant flex flex-col py-6 px-4 z-20">
<!-- Header -->
<div class="mb-8 px-3">
<h1 class="text-headline-md font-headline-md font-bold tracking-tight text-on-surface dark:text-on-surface">AndesContext</h1>
<p class="font-label-sm text-label-sm text-on-surface-variant mt-1">AI-Native Memory</p>
</div>
<!-- Navigation Tabs -->
<div class="flex-1 space-y-1">
<a class="flex items-center gap-3 py-2 px-3 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200 rounded-lg group" href="#">
<span class="material-symbols-outlined text-[20px] font-[200]">dashboard</span>
<span class="font-label-sm text-label-sm">Dashboard</span>
</a>
<a class="flex items-center gap-3 py-2 px-3 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200 rounded-lg group" href="#">
<span class="material-symbols-outlined text-[20px] font-[200]">folder_open</span>
<span class="font-label-sm text-label-sm">Repositories</span>
</a>
<a class="flex items-center gap-3 py-2 px-3 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200 rounded-lg group" href="#">
<span class="material-symbols-outlined text-[20px] font-[200]">auto_awesome_motion</span>
<span class="font-label-sm text-label-sm">Context Builder</span>
</a>
<!-- Active Tab -->
<a class="flex items-center gap-3 py-2 px-3 text-primary dark:text-primary font-bold border-l-2 border-primary pl-3 bg-surface-container-high/50 rounded-r-lg group relative" href="#">
<div class="absolute inset-0 bg-primary/5 rounded-r-lg"></div>
<span class="material-symbols-outlined text-[20px] font-[300] relative z-10">memory</span>
<span class="font-label-sm text-label-sm relative z-10">Memory</span>
</a>
<a class="flex items-center gap-3 py-2 px-3 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200 rounded-lg group" href="#">
<span class="material-symbols-outlined text-[20px] font-[200]">query_stats</span>
<span class="font-label-sm text-label-sm">Benchmarks</span>
</a>
<a class="flex items-center gap-3 py-2 px-3 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors duration-200 rounded-lg group" href="#">
<span class="material-symbols-outlined text-[20px] font-[200]">settings</span>
<span class="font-label-sm text-label-sm">Settings</span>
</a>
</div>
<!-- Footer Stats / Status -->
<div class="mt-auto space-y-3 pt-6 border-t border-outline-variant/30">
<div class="flex items-center gap-3 px-3 text-on-surface-variant">
<div class="relative flex h-2 w-2">
<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary-fixed opacity-75"></span>
<span class="relative inline-flex rounded-full h-2 w-2 bg-secondary"></span>
</div>
<span class="font-status-dot text-status-dot">Backend: Online</span>
<span class="material-symbols-outlined text-[16px] ml-auto">sensors</span>
</div>
<div class="flex items-center gap-3 px-3 text-on-surface-variant">
<div class="relative flex h-2 w-2">
<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
<span class="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
</div>
<span class="font-status-dot text-status-dot">Ollama: Running</span>
<span class="material-symbols-outlined text-[16px] ml-auto">memory</span>
</div>
<div class="flex items-center gap-3 px-3 text-on-surface-variant/50">
<div class="relative flex h-2 w-2">
<span class="relative inline-flex rounded-full h-2 w-2 bg-outline-variant"></span>
</div>
<span class="font-status-dot text-status-dot">Cognee: Idle</span>
<span class="material-symbols-outlined text-[16px] ml-auto">psychology</span>
</div>
</div>
</nav>
<!-- Main Content Area -->
<main class="ml-sidebar-width flex-1 flex flex-col h-screen overflow-hidden bg-background">
<!-- TopAppBar Component -->
<header class="h-16 w-full sticky top-0 z-10 flex items-center justify-between px-container-margin border-b border-outline-variant/20 bg-[#020617]/80 backdrop-blur-sm">
<div class="flex items-center gap-4">
<h2 class="font-headline-sm text-headline-sm text-on-surface font-semibold">Memory Browser</h2>
</div>
<!-- Search and Actions -->
<div class="flex items-center gap-4">
<!-- Global Search -->
<div class="relative group">
<span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">search</span>
<input class="bg-[#0F172A] border border-outline-variant/30 text-on-surface font-body-md text-body-md rounded-md pl-10 pr-4 py-1.5 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 w-64 transition-all placeholder:text-on-surface-variant/50" placeholder="Search semantic space..." type="text"/>
<div class="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1">
<kbd class="font-code-md text-code-md text-on-surface-variant/50 border border-outline-variant/30 rounded px-1.5 text-[10px]">⌘</kbd>
<kbd class="font-code-md text-code-md text-on-surface-variant/50 border border-outline-variant/30 rounded px-1.5 text-[10px]">K</kbd>
</div>
</div>
<!-- Trailing Actions -->
<button class="text-on-surface-variant hover:text-on-surface hover:bg-surface-variant rounded-full p-2 transition-all group relative">
<span class="material-symbols-outlined text-[20px]">notifications</span>
<span class="absolute top-2 right-2 w-2 h-2 bg-primary rounded-full border border-background"></span>
</button>
<button class="text-on-surface-variant hover:text-on-surface hover:bg-surface-variant rounded-full p-2 transition-all">
<span class="material-symbols-outlined text-[20px]">account_circle</span>
</button>
<button class="bg-primary text-[#FFFFFF] font-label-sm text-label-sm px-4 py-2 rounded-md hover:bg-primary/90 transition-colors ml-2 shadow-[0_0_15px_rgba(59,130,246,0.2)]">
                     New Index
                 </button>
</div>
</header>
<!-- Scrollable Content -->
<div class="flex-1 overflow-y-auto p-container-margin">
<div class="max-w-[1440px] mx-auto flex gap-6 h-full flex-col xl:flex-row">
<!-- Left/Main Column: Data Grid -->
<div class="flex-1 flex flex-col min-w-0">
<!-- Filters & Controls Bar -->
<div class="flex items-center justify-between mb-4">
<div class="flex items-center gap-2">
<span class="font-label-sm text-label-sm text-on-surface-variant mr-2">Filters:</span>
<button class="px-3 py-1 bg-[#1E293B] border border-primary/30 rounded-full font-label-sm text-label-sm text-primary flex items-center gap-1.5 hover:bg-[#1E293B]/80 transition-colors">
<span class="w-1.5 h-1.5 rounded-full bg-primary"></span>
                                Vectors
                            </button>
<button class="px-3 py-1 bg-[#0F172A] border border-outline-variant/30 rounded-full font-label-sm text-label-sm text-on-surface-variant flex items-center gap-1.5 hover:border-outline-variant transition-colors">
<span class="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                                Graphs
                            </button>
<button class="px-3 py-1 bg-[#0F172A] border border-outline-variant/30 rounded-full font-label-sm text-label-sm text-on-surface-variant flex items-center gap-1.5 hover:border-outline-variant transition-colors">
                                Document
                            </button>
<button class="px-2 py-1 border border-dashed border-outline-variant/50 rounded-full font-label-sm text-label-sm text-on-surface-variant flex items-center gap-1 hover:text-on-surface transition-colors ml-2">
<span class="material-symbols-outlined text-[16px]">add</span>
                                Add Filter
                            </button>
</div>
<div class="flex items-center gap-2">
<button class="text-on-surface-variant hover:text-on-surface p-1 rounded transition-colors" title="Grid View">
<span class="material-symbols-outlined text-[20px]">grid_view</span>
</button>
<button class="text-primary bg-primary/10 p-1 rounded transition-colors" title="List View">
<span class="material-symbols-outlined text-[20px]">view_list</span>
</button>
<div class="w-px h-4 bg-outline-variant/50 mx-1"></div>
<button class="text-on-surface-variant hover:text-on-surface p-1 rounded transition-colors flex items-center gap-1 text-label-sm font-label-sm">
<span class="material-symbols-outlined text-[18px]">sort</span>
                                Date Added
                            </button>
</div>
</div>
<!-- Dataset Table/List (Bento style integration) -->
<div class="bg-[#0F172A] border border-[#1E293B] rounded-lg overflow-hidden flex-1 flex flex-col">
<!-- Table Header -->
<div class="grid grid-cols-[2fr_1fr_1fr_1.5fr_auto] gap-4 p-4 border-b border-[#1E293B] bg-[#0F172A]/50">
<div class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Dataset / Source Repo</div>
<div class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Type</div>
<div class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider text-right">Size</div>
<div class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Creation Date</div>
<div class="w-8"></div>
</div>
<!-- Table Body (Scrollable) -->
<div class="overflow-y-auto flex-1">
<!-- Row 1 -->
<div class="grid grid-cols-[2fr_1fr_1fr_1.5fr_auto] gap-4 p-4 border-b border-[#1E293B]/50 items-center hover:bg-[#1E293B]/20 transition-colors group cursor-pointer relative">
<div class="absolute left-0 top-0 bottom-0 w-1 bg-primary scale-y-0 group-hover:scale-y-100 transition-transform origin-left"></div>
<div class="flex items-center gap-3">
<div class="w-8 h-8 rounded bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
<span class="material-symbols-outlined text-[18px]">data_object</span>
</div>
<div>
<div class="font-body-md text-body-md font-medium text-on-surface">core-auth-services</div>
<div class="font-code-md text-code-md text-on-surface-variant/70 text-[11px] mt-0.5">github.com/org/core-auth</div>
</div>
</div>
<div>
<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-status-dot bg-surface-variant text-on-surface-variant border border-outline-variant/30">
<span class="w-1.5 h-1.5 rounded-full bg-primary"></span>
                                        Vector DB
                                    </span>
</div>
<div class="font-code-md text-code-md text-on-surface-variant text-right">
                                    245 MB
                                </div>
<div class="font-body-md text-body-md text-on-surface-variant flex items-center gap-2">
<span>2 hours ago</span>
<span class="text-[10px] text-on-surface-variant/50 font-code-md">v1.2.4</span>
</div>
<div class="relative">
<button class="p-1.5 text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity hover:bg-surface-variant rounded" onclick="toggleMenu('menu-1')">
<span class="material-symbols-outlined text-[18px]">more_vert</span>
</button>
<!-- Context Menu (Hidden by default) -->
<div class="absolute right-0 top-8 w-40 bg-[#1E293B] border border-outline-variant/50 rounded-md shadow-[0_10px_25px_-5px_rgba(0,0,0,0.5)] py-1 z-20 hidden" id="menu-1">
<button class="w-full text-left px-3 py-1.5 font-label-sm text-label-sm text-on-surface hover:bg-surface-variant flex items-center gap-2">
<span class="material-symbols-outlined text-[16px]">refresh</span> Re-index
                                        </button>
<button class="w-full text-left px-3 py-1.5 font-label-sm text-label-sm text-on-surface hover:bg-surface-variant flex items-center gap-2">
<span class="material-symbols-outlined text-[16px]">download</span> Export
                                        </button>
<div class="h-px bg-outline-variant/30 my-1"></div>
<button class="w-full text-left px-3 py-1.5 font-label-sm text-label-sm text-error hover:bg-error/10 flex items-center gap-2" onclick="showConfirm()">
<span class="material-symbols-outlined text-[16px]">delete</span> Forget Dataset
                                        </button>
</div>
</div>
</div>
</div>
</div>
</div>
<!-- Right Column: Context/Stats Sidebar -->
<div class="w-full xl:w-80 flex flex-col gap-6">
<!-- Global Memory Stats Card -->
<div class="bg-[#0F172A] border border-[#1E293B] rounded-lg p-5 relative overflow-hidden group">
<!-- Subtle Ambient Glow -->
<div class="absolute -top-10 -right-10 w-32 h-32 bg-primary/10 rounded-full blur-3xl group-hover:bg-primary/20 transition-all duration-700"></div>
<h3 class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-4 flex items-center gap-2">
<span class="material-symbols-outlined text-[16px]">database</span>
                            Memory Topology
                        </h3>
<div class="space-y-4">
<div>
<div class="font-code-md text-code-md text-on-surface-variant/70 text-[11px] mb-1">Total Stored Data</div>
<div class="font-display text-display text-on-surface flex items-baseline gap-1">
                                    1.2 <span class="text-headline-md text-on-surface-variant font-medium">TB</span>
</div>
</div>
<div class="grid grid-cols-2 gap-4 pt-3 border-t border-[#1E293B]/50">
<div>
<div class="font-code-md text-code-md text-on-surface-variant/70 text-[11px] mb-1">Graph Nodes</div>
<div class="font-headline-md text-headline-md text-on-surface font-semibold">14.2M</div>
</div>
<div>
<div class="font-code-md text-code-md text-on-surface-variant/70 text-[11px] mb-1">Graph Edges</div>
<div class="font-headline-md text-headline-md text-on-surface font-semibold text-secondary">38.5M</div>
</div>
</div>
</div>
</div>
</div>
</div>
</div>
</main>
<!-- Confirmation Modal (Hidden by default) -->
<div class="fixed inset-0 z-50 flex items-center justify-center bg-[#020617]/80 backdrop-blur-sm hidden opacity-0 transition-opacity duration-200" id="forget-modal">
<div class="bg-[#0F172A] border border-[#1E293B] rounded-xl shadow-[0_20px_50px_-12px_rgba(0,0,0,0.8)] w-[400px] overflow-hidden transform scale-95 transition-transform duration-200" id="modal-content">
<div class="p-6">
<div class="w-12 h-12 rounded-full bg-error/10 border border-error/20 flex items-center justify-center text-error mb-4">
<span class="material-symbols-outlined text-[24px]">warning</span>
</div>
<h3 class="font-headline-md text-headline-md text-on-surface font-semibold mb-2">Forget Dataset</h3>
<p class="font-body-md text-body-md text-on-surface-variant mb-4">
                    Are you sure you want to permanently delete the memory index for <strong class="text-on-surface font-code-md">core-auth-services</strong>? 
                </p>
<p class="font-body-md text-body-md text-on-surface-variant text-[13px] border-l-2 border-error/50 pl-3 py-1 bg-error/5 rounded-r">
                    This action cannot be undone and will remove 245 MB of vector embeddings.
                </p>
</div>
<div class="px-6 py-4 bg-[#1E293B]/50 border-t border-[#1E293B] flex justify-end gap-3">
<button class="px-4 py-2 rounded-md font-label-sm text-label-sm text-on-surface hover:bg-surface-variant border border-transparent transition-colors" onclick="hideConfirm()">
                    Cancel
                </button>
<button class="px-4 py-2 rounded-md font-label-sm text-label-sm bg-error text-[#FFFFFF] hover:bg-error/90 transition-colors shadow-[0_0_10px_rgba(255,180,171,0.2)]" onclick="hideConfirm()">
                    Forget Dataset
                </button>
</div>
</div>
</div>
<script>
        function toggleMenu(id) {
            const menu = document.getElementById(id);
            // Hide all other menus first in a real app
            if(menu.classList.contains('hidden')) {
                menu.classList.remove('hidden');
            } else {
                menu.classList.add('hidden');
            }
        }
        
        // Close menus when clicking outside
        document.addEventListener('click', function(event) {
            const isClickInside = event.target.closest('.relative');
            if (!isClickInside) {
                const menus = document.querySelectorAll('[id^="menu-"]');
                menus.forEach(m => m.classList.add('hidden'));
            }
        });

        const modal = document.getElementById('forget-modal');
        const modalContent = document.getElementById('modal-content');

        function showConfirm() {
            // Close the dropdown first
            document.querySelectorAll('[id^="menu-"]').forEach(m => m.classList.add('hidden'));
            
            modal.classList.remove('hidden');
            // Trigger reflow
            void modal.offsetWidth;
            modal.classList.remove('opacity-0');
            modalContent.classList.remove('scale-95');
        }

        function hideConfirm() {
            modal.classList.add('opacity-0');
            modalContent.classList.add('scale-95');
            setTimeout(() => {
                modal.classList.add('hidden');
            }, 200);
        }
    </script>
</body></html>