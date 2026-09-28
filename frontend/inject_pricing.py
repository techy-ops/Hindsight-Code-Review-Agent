import re
import os

filepath = r"c:\Users\krish\OneDrive\Desktop\Ai-code-review-agent\frontend\pricing\pricing.html"

pricing_html = """
    <main class="max-w-7xl mx-auto px-6 py-12">
        <section class="text-center mb-16">
            <h1 class="text-5xl md:text-6xl font-black mb-6 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-primary to-purple-400">
                Simple, transparent pricing
            </h1>
            <p class="text-xl text-slate-400 max-w-2xl mx-auto">
                Choose the plan that best fits your needs. No hidden fees.
            </p>
        </section>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <div class="glass p-8 rounded-2xl border border-border-dark flex flex-col">
                <h3 class="text-2xl font-bold mb-2">Hobby</h3>
                <p class="text-slate-400 text-sm mb-6">Perfect for individual developers.</p>
                <div class="mb-6">
                    <span class="text-4xl font-black">$0</span>
                    <span class="text-slate-400">/mo</span>
                </div>
                <ul class="space-y-4 mb-8 flex-1">
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-primary text-sm">check_circle</span> 100 Analyses / month</li>
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-primary text-sm">check_circle</span> Basic Vulnerability Detection</li>
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-slate-600 text-sm">cancel</span> Advanced Optimization</li>
                </ul>
                <button onclick="window.location.href='/create_account/signup.html'" class="w-full py-3 px-6 bg-surface-dark border border-primary/30 text-white font-bold rounded-xl hover:bg-primary/20 transition-all">Get Started</button>
            </div>
            
            <div class="glass p-8 rounded-2xl border-2 border-primary relative flex flex-col transform md:-translate-y-4 shadow-2xl glow-shadow">
                <div class="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary text-white text-xs font-bold px-4 py-1 rounded-full uppercase tracking-wider">Most Popular</div>
                <h3 class="text-2xl font-bold mb-2">Pro</h3>
                <p class="text-slate-400 text-sm mb-6">For professional developers and small teams.</p>
                <div class="mb-6">
                    <span class="text-4xl font-black">$19</span>
                    <span class="text-slate-400">/mo</span>
                </div>
                <ul class="space-y-4 mb-8 flex-1">
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-primary text-sm">check_circle</span> Unlimited Analyses</li>
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-primary text-sm">check_circle</span> Advanced Optimization</li>
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-primary text-sm">check_circle</span> API Access</li>
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-primary text-sm">check_circle</span> Priority Support</li>
                </ul>
                <button onclick="window.location.href='/create_account/signup.html'" class="w-full py-3 px-6 code-gradient text-white font-bold rounded-xl hover:opacity-90 transition-all">Start Free Trial</button>
            </div>
            
            <div class="glass p-8 rounded-2xl border border-border-dark flex flex-col">
                <h3 class="text-2xl font-bold mb-2">Enterprise</h3>
                <p class="text-slate-400 text-sm mb-6">For large organizations with custom needs.</p>
                <div class="mb-6">
                    <span class="text-4xl font-black">Custom</span>
                </div>
                <ul class="space-y-4 mb-8 flex-1">
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-primary text-sm">check_circle</span> Everything in Pro</li>
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-primary text-sm">check_circle</span> Custom Integrations</li>
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-primary text-sm">check_circle</span> Dedicated Account Manager</li>
                    <li class="flex items-center gap-3"><span class="material-symbols-outlined text-primary text-sm">check_circle</span> SLA Guarantee</li>
                </ul>
                <button onclick="window.location.href='/platform_documentation/documentation.html'" class="w-full py-3 px-6 bg-surface-dark border border-border-dark text-white font-bold rounded-xl hover:bg-surface-dark/80 transition-all">Contact Sales</button>
            </div>
        </div>
    </main>
"""

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace <main>...</main>
new_content = re.sub(r'<main.*?</main>', pricing_html, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Pricing page updated")
