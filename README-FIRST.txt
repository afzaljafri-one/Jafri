JAFRI.ONE — FINAL GITHUB WEBSITE PACKAGE

This is the complete static website package for jafri.one. It preserves the existing site pages and assets and includes the interactive Career dashboard refinement.

PAGES
- index.html — homepage and career snapshot.
- career.html — interactive career dashboard. Select an employer in the left column to update the detailed role profile on the right. Each employer row includes its logo, role and dates, plus a separate external website link. The detail panel includes mandate / KRAs, work delivered, outcomes, relevant metrics and internal case-study links where available.
- work.html — selected business portfolio.
- payments-ecosystem.html — payments ecosystem guide.
- fastag.html — B2B FASTag case study.
- ncmc.html — NCMC case study.
- mobility.html — digital payments and mobility case study.
- 404.html — custom not-found page.

NAVIGATION
All eight HTML pages use the same navigation order: About, Impact, Expertise, Career, Payment Ecosystem, B2B FASTag, NCMC, Mobility, Contact. The text wordmark is consistent across pages.

CAREER DASHBOARD
- Full-width dark navy / gold executive layout inspired by the approved career mockup.
- Career hero, statistics and chapter filters.
- Two-column interactive company selector and detailed role profile.
- 18 career role entries, including both Meru tenures.
- Official employer website links are available from the left-side list and the employer detail panel.
- The three locally supplied company marks (Airtel Payments Bank, Meru Cabs and TaxiForSure) are hosted in assets/company-logos. Other employer marks use favicon sources with a text fallback if an image cannot load.
- Historical figures and overlapping early-career dates are identified cautiously; profile-derived metrics should be checked for period and scope before being represented as audited results.

SITE / SEO FILES
- CNAME — custom domain jafri.one.
- .nojekyll — GitHub Pages static asset handling.
- robots.txt and sitemap.xml.
- favicon.ico.

ANALYTICS
Existing analytics identifiers are retained where present in the source pages. This package does not create or change any external analytics accounts.

GITHUB PUBLISHING
1. Download and extract this ZIP.
2. Back up the current GitHub repository before replacing files.
3. Upload the contents inside the JafriOne_GitHub_Full_Site folder to the ROOT of the existing repository (not the enclosing folder).
4. Commit the changes to the main branch.
5. Allow GitHub Pages to complete deployment, then test https://jafri.one/ and https://jafri.one/career.html.

LOCAL PREVIEW
For the most reliable local preview, run a local static server from the extracted folder rather than opening HTML files directly with file://. Example: python3 -m http.server 8000, then open http://localhost:8000/. Reset browser zoom to 100% (Mac: Command + 0) when comparing the page with the supplied full-size mockup.

POST-DEPLOYMENT CHECKS
- Check all nine navigation items on desktop and mobile.
- On career.html, click several employers and verify the right-side profile changes.
- Test employer external links and internal case-study links.
- Confirm logos and the career hero background load.
- Check /robots.txt and /sitemap.xml.
- Confirm the custom domain and HTTPS remain active in GitHub Pages.

This ZIP contains website source files and assets only. It does not change GitHub repository settings, DNS, domain registration, Search Console, GA4 or Microsoft Clarity configuration. Live deployment must be verified after pushing to GitHub.
