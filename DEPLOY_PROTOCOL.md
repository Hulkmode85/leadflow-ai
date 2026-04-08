# LeadFlow AI - Deploy Protocol

## Live URLs
- **App (Railway):** https://leadflow-engine-production.up.railway.app
- **Landing (GitHub Pages):** https://hulkmode85.github.io/leadflow-ai-landing/
- **Railway Project ID:** 62c30c09-be7e-4081-b62b-3e4cc3d61f4c
- **Service ID:** 570c8fcd-2191-4396-a507-27a99fe80037

## Go-Live Checklist (Tonight)
1. Set real ANTHROPIC_API_KEY in Railway env vars (currently placeholder)
2. Verify app loads at Railway URL -> /search
3. Run test search: "dentists in San Jose, CA" -> confirm 15 scored leads
4. Export CSV -> confirm download works
5. Optional: Set GOOGLE_MAPS_API_KEY for real business data (mock data works without it)

## Primary Use: Internal Lead-Gen for Businesses 1-3
LeadFlow is FIRST an internal tool to find clients for:
- **Business 1 (AI Automation Service):** Search "[niche] in [city]" -> export high-score leads -> cold email
- **Business 2 (Micro-SaaS):** Find businesses with no website/email (score 8+) -> pitch AI chatbot
- **Business 3 (Content Repurposing):** Find businesses with outdated social -> pitch content service

### Internal Workflow
1. Search target niche + city in LeadFlow
2. Export CSV of leads scored 7+
3. Feed CSV into cold email pipeline (Business 1 outreach templates)
4. Track responses in CRM
5. Repeat for new cities/niches weekly

## Productization Roadmap ($299/$599/$999/mo)
### Starter ($299/mo)
- 500 lead searches/month
- Heuristic scoring (no AI)
- CSV export
- Email support

### Pro ($599/mo)
- 2,000 lead searches/month
- Claude Haiku AI scoring
- API access
- Priority support
- CRM integration (Zapier)

### Enterprise ($999/mo)
- Unlimited searches
- Google Maps real data
- Custom scoring criteria
- Dedicated onboarding
- White-label option

## Integration: Outreach Templates (Business 1)
CSV export columns map directly to outreach personalization:
- Name -> company name in subject line
- Score -> urgency tier (8+ = immediate, 5-7 = nurture, <5 = drip)
- Approach -> email angle/hook
- Website -> "I noticed your website..." or "I noticed you don't have a website..."
- Rating/Reviews -> "Your 2.3-star rating suggests customers want better..."

## CSV Export -> Cold Email Automation Pipeline
1. Export CSV from LeadFlow
2. Filter: keep score >= 7
3. Upload to email tool (Instantly.ai / Smartlead / Lemlist)
4. Map columns: Name, Email, Approach -> template variables
5. Send sequences:
   - Day 1: Personalized cold email using Approach column
   - Day 3: Follow-up with case study
   - Day 7: Final touch with free audit offer
6. Track opens/replies -> feed back into scoring model

## Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| ANTHROPIC_API_KEY | Claude API key for AI scoring | Optional (falls back to heuristic) |
| GOOGLE_MAPS_API_KEY | Google Places API for real data | Optional (uses mock data) |
| SECRET_KEY | Flask session secret | Set automatically |
| PORT | Server port | Set by Railway |

## Redeploy
Push to GitHub main branch -> Railway auto-deploys.
Manual trigger: variableUpsert(BUILD_TS) via Railway API.