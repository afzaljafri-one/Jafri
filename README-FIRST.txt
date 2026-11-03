JAFRI.ONE — FULL WEBSITE PACKAGE

This is the complete static-site package assembled from the previously saved full website package, with the approved homepage employer-logo update and the new Payments Ecosystem page integrated.

ROOT PAGES
- index.html — homepage; updated Career Journey employer logos and Payments navigation.
- fastag.html — B2B FASTag case study.
- ncmc.html — NCMC case study / explainer.
- mobility.html — Mobility payments page.
- payments-ecosystem.html — black-and-gold payments guide.
- career.html — detailed chronological career history with employer links and logos.
- work.html — selected business portfolio with internal case-study links.
- 404.html — custom not-found page.

SITE / SEO FILES
- CNAME — custom domain jafri.one.
- .nojekyll — GitHub Pages static asset handling.
- robots.txt — crawler access and sitemap declaration.
- sitemap.xml — all seven canonical pages.
- favicon.ico — site favicon.

ASSETS
- `assets/` contains the original supplied site images, page illustrations, portraits, company marks, social preview images, WhatsApp icon and signature logo.
- `assets/company-logos/` contains polished locally hosted Airtel Payments Bank, Meru Cabs and TaxiForSure logos used on the homepage.

ANALYTICS
The homepage and existing case-study pages retain the existing tracking IDs:
- Google Analytics 4: G-MTJ0FR8T4P
- Microsoft Clarity: z7iblovjp4
The new Payments Ecosystem page uses the same IDs. No new GA4 property or Clarity project was created.

DEPLOYMENT
1. Extract this ZIP.
2. Upload the entire extracted contents to the root of the existing GitHub repository `afzaljafri-one/Jafri` on the `main` branch.
3. This package is intended as a complete root-site replacement. Keep a backup of the current repository before replacing it.
4. Confirm the repository root contains index.html, fastag.html, ncmc.html, mobility.html, payments-ecosystem.html, 404.html, CNAME, .nojekyll, robots.txt, sitemap.xml, favicon.ico and the assets folder.
5. Commit and push. GitHub Pages should serve the domain jafri.one.

POST-DEPLOYMENT QA
- Open https://jafri.one/ and verify homepage sections, portraits, logo assets and navigation.
- Open /fastag.html, /ncmc.html, /mobility.html and /payments-ecosystem.html.
- Check desktop and mobile layouts.
- Open /robots.txt and /sitemap.xml.
- In Google Search Console, submit https://jafri.one/sitemap.xml and inspect each canonical page.
- In GA4 Realtime, confirm page_view events and page_path for each page.
- In Microsoft Clarity, confirm page visits and recordings after sufficient traffic.
- Validate structured data with Schema Markup Validator and check page metadata / canonical URLs.

IMPORTANT
This package includes all pages and assets from the saved full website archive available to this build. It does not include GitHub repository settings, DNS configuration, Search Console account settings, or any external integrations not represented in the supplied website files. SEO metadata and tracking code are present, but indexing, search ranking and analytics data collection must still be verified after deployment.
