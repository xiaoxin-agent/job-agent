/**
 * Job Extractor - Content Script
 * Runs on every page. When popup requests extraction, scrapes
 * the DOM using multiple strategies and returns structured data.
 *
 * v2: rewritten for robustness — LinkedIn uses dynamic class names,
 *     so we rely on JSON-LD + aria labels + common patterns.
 */

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extract_job') {
    sendResponse(extractJob());
  }
  return true;
});

/**
 * Main extraction entry point.
 */
function extractJob() {
  const result = {
    title: '',
    company: '',
    location: '',
    description: '',
    job_type: '',
    url: window.location.href,
    source: window.location.origin,
    extracted_by: 'content_script_v2',
    strategies_used: [],
  };

  // Strategy 1: JSON-LD (works on most modern job sites including LinkedIn)
  tryJsonLd(result);

  // Strategy 2: Meta / OG tags (fallback for title, company, description)
  tryMetaTags(result);

  // Strategy 3: Site-specific extractors
  const host = window.location.hostname.toLowerCase();

  if (host.includes('linkedin.com')) {
    tryLinkedInDOM(result);
  } else if (host.includes('indeed.com')) {
    tryIndeedDOM(result);
  } else if (host.includes('glassdoor.com')) {
    tryGlassdoorDOM(result);
  } else if (host.includes('greenhouse.io')) {
    tryGreenhouseDOM(result);
  } else if (host.includes('lever.co')) {
    tryLeverDOM(result);
  } else if (host.includes('workday.com')) {
    tryWorkdayDOM(result);
  }

  // Strategy 4: Universal fallback — scrape visible text
  if (!result.description || result.description.length < 200) {
    tryDomTextFallback(result);
  }

  // Strategy 5: Try to find job title / company from the <title> tag
  if (!result.title) {
    const t = document.title;
    if (t) {
      // Clean common job board suffixes
      result.title = t.replace(/\s*[|\-–—].+$/, '').trim();
      result.strategies_used.push('title-tag');
    }
  }

  if (!result.company && result.source) {
    tryCompanyFromURL(result);
  }

  // Clean up
  if (result.description) {
    result.description = cleanText(result.description);
    result.strategies_used.push('clean');
  }

  return result;
}

/* ════════════════════════════════════════════
   JSON-LD
   ════════════════════════════════════════════ */

function tryJsonLd(result) {
  const scripts = document.querySelectorAll('script[type="application/ld+json"]');
  if (!scripts.length) return;

  for (const script of scripts) {
    try {
      let data = JSON.parse(script.textContent);
      // Unwrap @graph
      if (data['@graph']) {
        data = data['@graph'].find(item => item['@type'] === 'JobPosting') || data;
      }
      if (Array.isArray(data)) {
        data = data.find(item => item['@type'] === 'JobPosting') || data[0];
      }
      if (!data || data['@type'] !== 'JobPosting') continue;

      if (data.title) result.title = data.title;

      if (data.description) result.description = data.description;

      const org = data.hiringOrganization;
      if (org) {
        result.company = typeof org === 'string' ? org :
                         org.name ? org.name : result.company;
      }

      const loc = data.jobLocation;
      if (loc) {
        if (typeof loc === 'string') {
          result.location = loc;
        } else if (loc.address) {
          const a = typeof loc.address === 'string' ? { addressLocality: loc.address }
                    : loc.address;
          const parts = [a.addressLocality, a.addressRegion,
                         typeof a.addressCountry === 'object' ? a.addressCountry.name
                         : a.addressCountry].filter(Boolean);
          result.location = parts.join(', ') || loc.name || '';
        } else if (loc.name) {
          result.location = loc.name;
        }
      }

      if (data.employmentType) {
        result.job_type = Array.isArray(data.employmentType)
          ? data.employmentType.join(', ') : data.employmentType;
      }

      result.strategies_used.push('jsonld');

      // If we got title + company from JSON-LD, that's solid
      if (result.title && result.company) return;
    } catch (e) {
      // skip
    }
  }
}

/* ════════════════════════════════════════════
   Meta / OG Tags
   ════════════════════════════════════════════ */

function tryMetaTags(result) {
  if (!result.title) {
    const ogTitle = getMeta('og:title');
    if (ogTitle) {
      result.title = ogTitle
        .replace(/\s*\|\s*LinkedIn\s*$/, '')  // " | LinkedIn"
        .replace(/\s*[-–—|].*$/, '')            // title - suffix
        .trim();
    } else {
      const titleTag = document.querySelector('title');
      if (titleTag) {
        result.title = titleTag.textContent.trim()
          .replace(/\s*[-–—|].*$/, '')
          .trim();
      }
    }
  }

  if (!result.company) {
    // Try LinkedIn-specific: article:author
    let c = getMeta('article:author');
    if (!c) c = getMeta('og:site_name');
    if (c) {
      // Clean " on LinkedIn" suffix etc
      result.company = c.replace(/\s*on\s+LinkedIn\s*$/i, '').trim();
    }
  }

  if (!result.description || result.description.length < 100) {
    let d = getMeta('og:description') || getMeta('description');
    if (d && d.length > 80) result.description = d;
  }

  // Try to extract company from og:title "Company hiring Title | LinkedIn"
  if (!result.company && result.title) {
    const m = result.title.match(/^(.+?)\s+(?:hiring|is hiring|is looking for|jobs?)\s+/i);
    if (m) result.company = m[1].trim();
  }

  if (result.title || result.description) {
    result.strategies_used.push('meta');
  }
}

function getMeta(property) {
  const el = document.querySelector(`meta[property="${property}"]`) ||
             document.querySelector(`meta[name="${property}"]`);
  return el ? el.getAttribute('content') : null;
}

/* ════════════════════════════════════════════
   LinkedIn DOM
   ════════════════════════════════════════════ */

function tryLinkedInDOM(result) {
  result.strategies_used.push('linkedin');

  // LinkedIn uses dynamic BEM class names like
  // jobs-unified-top-card__job-title, jobs-details__main-content etc.
  // We use attribute-contains selectors to be class-name agnostic.

  // -- Title --
  // Try h1 with job-related text
  const h1 = document.querySelector('h1');
  if (h1 && !result.title) {
    const t = h1.textContent.trim();
    if (t.length > 5 && t.length < 300) {
      result.title = t;
    }
  }

  // Try any element with class containing "job-title" (dynamic BEM)
  const titleCandidates = document.querySelectorAll(
    '[class*="job-title"], [class*="jobTitle"], [class*="top-card"]'
  );
  for (const el of titleCandidates) {
    const t = el.textContent.trim();
    if (t.length > 5 && t.length < 300 && /[a-zA-Z]/.test(t)) {
      result.title = t;
      break;
    }
  }

  // -- Company --
  // LinkedIn often has: <a class="...company-name..."> or inside top-card
  const companyCandidates = document.querySelectorAll(
    '[class*="company-name"], [class*="companyName"], [class*="org-name"], ' +
    '[class*="top-card"] a[href*="/company/"], ' +
    '[class*="topcard"] a[href*="/company/"]'
  );
  for (const el of companyCandidates) {
    const t = el.textContent.trim();
    if (t.length > 1 && t.length < 200) {
      result.company = t;
      break;
    }
  }

  // -- Location --
  // Look for location in the top card area (often next to company)
  const locCandidates = document.querySelectorAll(
    '[class*="location"], [class*="bulleted"], [class*="top-card"] span, ' +
    '[class*="topcard"] span'
  );
  for (const el of locCandidates) {
    const t = el.textContent.trim();
    if (/[A-Za-z]/.test(t) &&
        (t.includes(',') || t.includes('Canada') || t.includes('US') ||
         t.includes('Remote') || t.includes('Toronto') || t.includes('Vancouver') ||
         t.includes('Ontario') || t.includes('United States'))) {
      result.location = t;
      break;
    }
  }

  // -- Description --
  // LinkedIn's job description lives in show-more-less-html__markup or similar
  const descSelectors = [
    '.show-more-less-html__markup',
    '[class*="show-more-less"]',
    '[class*="job-description"]',
    '[class*="description__text"]',
    'article',
    // The main details container
    '[class*="jobs-details"]',
    '[class*="jobs-description"]',
  ];

  for (const sel of descSelectors) {
    const el = document.querySelector(sel);
    if (!el) continue;

    // Try to get structured innerText (preserves line breaks)
    const text = el.innerText || el.textContent;
    if (text && text.trim().length > 200) {
      result.description = text.trim();
      const des = el.querySelector('.show-more-less-html__markup');
      if (des) result.description = des.innerText || des.textContent;
      break;
    }
  }

  // If still no description but we found a description via JSON-LD or meta,
  // that's fine; don't overwrite it with garbage.

  // -- Job type from meta or JSON-LD only for LinkedIn (DOM unreliable) --
}

/* ════════════════════════════════════════════
   Indeed
   ════════════════════════════════════════════ */

function tryIndeedDOM(result) {
  result.strategies_used.push('indeed');

  const titleEl = document.querySelector('h1') ||
                  document.querySelector('[class*="jobTitle"]') ||
                  document.querySelector('[data-testid="jobTitle"]');
  if (titleEl && !result.title) result.title = titleEl.textContent.trim();

  const companyEl = document.querySelector('[data-company-name]') ||
                    document.querySelector('[class*="companyName"]') ||
                    document.querySelector('[class*="company-name"]');
  if (companyEl && !result.company) result.company = companyEl.textContent.trim();

  const locEl = document.querySelector('[data-testid="job-location"]') ||
                document.querySelector('[class*="location"]');
  if (locEl && !result.location) result.location = locEl.textContent.trim();

  const descEl = document.querySelector('#jobDescriptionText') ||
                 document.querySelector('[class*="jobsearch-JobComponent-description"]');
  if (descEl) result.description = descEl.innerText || descEl.textContent;
}

/* ════════════════════════════════════════════
   Glassdoor
   ════════════════════════════════════════════ */

function tryGlassdoorDOM(result) {
  result.strategies_used.push('glassdoor');

  const titleEl = document.querySelector('h1[class*="title"]') ||
                  document.querySelector('h1');
  if (titleEl && !result.title) result.title = titleEl.textContent.trim();

  const companyEl = document.querySelector('[class*="employer"] a, [class*="company"] a') ||
                    document.querySelector('[class*="employer-name"]');
  if (companyEl && !result.company) result.company = companyEl.textContent.trim();

  const descEl = document.querySelector('[class*="description"]');
  if (descEl) result.description = descEl.innerText || descEl.textContent;
}

/* ════════════════════════════════════════════
   Greenhouse
   ════════════════════════════════════════════ */

function tryGreenhouseDOM(result) {
  result.strategies_used.push('greenhouse');

  const titleEl = document.querySelector('.app-title, h1');
  if (titleEl && !result.title) result.title = titleEl.textContent.trim();

  // Company often in header logo or meta
  if (!result.company) {
    const logo = document.querySelector('.logo a, .header a');
    if (logo) result.company = logo.textContent.trim();
  }

  const descEl = document.querySelector('#content, .posting-description');
  if (descEl) result.description = descEl.innerText || descEl.textContent;
}

/* ════════════════════════════════════════════
   Lever
   ════════════════════════════════════════════ */

function tryLeverDOM(result) {
  result.strategies_used.push('lever');

  const titleEl = document.querySelector('.posting-headline h2, h1');
  if (titleEl && !result.title) result.title = titleEl.textContent.trim();

  const descEl = document.querySelector('.posting-page-content, .content, .page-content');
  if (descEl) result.description = descEl.innerText || descEl.textContent;
}

/* ════════════════════════════════════════════
   Workday
   ════════════════════════════════════════════ */

function tryWorkdayDOM(result) {
  result.strategies_used.push('workday');
  // Workday is a SPA with shadow DOM — best bet is JSON-LD which should already be caught
  // Try document title
  if (!result.title) {
    const t = document.title;
    if (t) result.title = t.replace(/\s*[-–—|].*$/, '').trim();
  }
}

/* ════════════════════════════════════════════
   Company from URL
   ════════════════════════════════════════════ */

function tryCompanyFromURL(result) {
  const hostname = window.location.hostname.replace('www.', '');
  const knownBoards = ['linkedin.com', 'indeed.com', 'glassdoor.com', 'monster.com',
                       'ziprecruiter.com', 'simplyhired.com', 'google.com',
                       'craigslist.org', 'dice.com', 'careerbuilder.com'];

  // Skip job boards
  if (knownBoards.some(d => hostname.includes(d))) return;

  // For company career pages, domain = company name
  const domain = hostname.split('.')[0];
  if (domain && domain.length > 2) {
    result.company = domain.charAt(0).toUpperCase() + domain.slice(1);
    result.strategies_used.push('url-company');
  }
}

/* ════════════════════════════════════════════
   Universal DOM text fallback
   ════════════════════════════════════════════ */

function tryDomTextFallback(result) {
  const body = document.body;
  if (!body) return;

  const clone = body.cloneNode(true);
  // Remove non-content elements
  clone.querySelectorAll(
    'script, style, nav, footer, header, aside, .sidebar, .nav, .footer, .header, ' +
    '[role="navigation"], [role="banner"], [role="contentinfo"]'
  ).forEach(el => el.remove());

  const allText = clone.innerText || clone.textContent;
  const lines = allText.split('\n').map(l => l.trim()).filter(l => l.length > 20);

  // Find the longest contiguous content block
  let best = '';
  let current = '';
  for (const line of lines) {
    if (line.length > 50) {
      current += line + '\n';
    } else {
      if (current.length > 400 && current.length > best.length) best = current;
      current = '';
    }
  }
  if (current.length > 400 && current.length > best.length) best = current;

  if (best) {
    // Heuristic: pick the block that has most job-related keywords
    const jobKeywords = /(responsibilit|qualification|requirement|experience|skill|position|role|job|salary|benefit)/gi;
    const keywordMatches = (best.match(jobKeywords) || []).length;

    // If we already have a shorter description but the new one is more job-like, use it
    if (!result.description || (keywordMatches > 5 && best.length > result.description.length)) {
      result.description = best;
      result.strategies_used.push('dom-fallback');
    }
  }
}

/* ════════════════════════════════════════════
   Text Cleaning
   ════════════════════════════════════════════ */

function cleanText(text) {
  if (!text) return '';

  // Strip HTML tags
  if (text.includes('<')) {
    const temp = document.createElement('div');
    temp.innerHTML = text;
    text = temp.innerText || temp.textContent;
  }

  return text
    .replace(/\r\n/g, '\n')
    .replace(/\t/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{4,}/g, '\n\n\n')
    .trim();
}
