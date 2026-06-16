# ICD-10 & CPT Code Data Sources - Complete Guide

## Problem
Your current CSV files are:
- ❌ Missing stage-specific codes (N18.31, N18.32)
- ❌ Truncated descriptions (58 chars limit)
- ❌ Have incorrect Z79 codes
- ❌ Not updated regularly
- ❌ Can't validate LLM-generated codes

---

## Solution: Use External APIs

### 🏆 **OPTION 1: UMLS (National Library of Medicine)** - BEST

| Feature | Details |
|---------|---------|
| **Cost** | FREE (requires registration) |
| **Accuracy** | ⭐⭐⭐⭐⭐ Authoritative, maintained by NIH |
| **Speed** | Real-time API (cached locally) |
| **Coverage** | ICD-10-CM + CPT + SNOMED (you can filter SNOMED out) |
| **Updates** | Monthly |
| **Licensing** | Public API, free for US healthcare |

**How to use:**
```
1. Register: https://www.nlm.nih.gov/research/umls/
2. Get API key immediately (free)
3. Use API to look up codes on-demand
4. Cache results in Django database
```

**Example:**
```python
from coding.umls_integration import UMLSCodeLookup

lookup = UMLSCodeLookup()

# Get accurate ICD-10 code
code_info = lookup.get_icd10_info("N18.31")
# Returns: {
#   "code": "N18.31",
#   "description": "Chronic kidney disease, stage 3a",
#   "cui": "C...",
# }

# Get all stage variants automatically
stages = lookup.get_icd10_stages("N18")
# Returns all: N18.1, N18.31, N18.32, N18.4, N18.5
```

**Advantages:**
✅ Free forever  
✅ Most authoritative source (NIH)  
✅ Real-time lookups  
✅ Can validate LLM-generated codes  
✅ No licensing restrictions  

---

### 📊 **OPTION 2: CMS Official Files** - MOST AUTHORITATIVE

| Feature | Details |
|---------|---------|
| **Cost** | FREE |
| **Accuracy** | ⭐⭐⭐⭐⭐ Official US government source |
| **Speed** | Batch download monthly |
| **Coverage** | ICD-10-CM only (perfect for you) |
| **Updates** | October 1st annually (minor updates quarterly) |
| **Licensing** | Public domain |

**How to use:**
```
1. Download from: https://www.cms.gov/medicare/coding-and-billing/icd-10-cm
2. Parse .txt or database file
3. Import into your database (monthly sync)
4. Lookup locally (fastest)
```

**Available files:**
- `icd10cm_codes_YYYY.txt` - Full list with descriptions
- `icd10cm_guidelines_YYYY.txt` - Coding rules
- `icd10cm_order_YYYY.txt` - Code order/hierarchy

**Example parse:**
```python
# File contains:
# N18   Chronic kidney disease
# N18.1 Stage 1
# N18.2 Stage 2
# N18.31 Stage 3a
# N18.32 Stage 3b
# N18.4 Stage 4
# N18.5 Stage 5
```

**Advantages:**
✅ Most authoritative  
✅ Complete descriptions (no truncation)  
✅ Official coding guidelines included  
✅ Once downloaded, super fast  

---

### 💳 **OPTION 3: AMA CPT Data** - For CPT Codes (PAID)

| Feature | Details |
|---------|---------|
| **Cost** | ~$500-1500/year per license |
| **Accuracy** | ⭐⭐⭐⭐⭐ Official CPT source |
| **Speed** | API access |
| **Coverage** | CPT codes only |
| **Updates** | Annual (Jan 1) |
| **Licensing** | Licensed use only (restricted) |

**Why expensive:**
- AMA owns CPT copyright
- License required for commercial use
- Updates released January 1st annually

**Free alternative:**
CMS publishes CPT descriptions in their RVU (Relative Value Unit) files:
```
https://www.cms.gov/apps/physician-fee-schedule/
```

---

### 🔄 **OPTION 4: Hybrid Approach (RECOMMENDED)** ⭐⭐⭐⭐⭐

**Best of all worlds:**

```
┌─────────────────┐
│  LLM generates  │
│  codes (N18.31) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ 1. Check local Django DB    │  (fast, cached)
│    if code exists           │
└────────┬────────────────────┘
         │
         ├─ Found? Return ✓
         │
         └─ Not found?
            │
            ▼
         ┌─────────────────────────────┐
         │ 2. Query UMLS API           │  (accurate, real-time)
         │    (with cache)             │
         └────────┬────────────────────┘
                  │
                  ├─ Found? Cache + Return ✓
                  │
                  └─ Not found?
                     │
                     ▼
                  ┌─────────────────────────────┐
                  │ 3. Flag for human review    │  (safety)
                  │    CODE NOT FOUND           │
                  └─────────────────────────────┘
```

**Implementation:**
```python
def get_code_description(system: str, code: str) -> dict:
    """Get code info using hybrid approach."""
    
    # 1. Try local database (fastest)
    db_code = ICD10Code.objects.filter(code=code).first()
    if db_code:
        return {
            "code": code,
            "description": db_code.description,
            "source": "local_cache",
        }
    
    # 2. Try UMLS API (accurate, caches locally)
    umls_result = UMLSCodeLookup.get_icd10_info(code)
    if umls_result:
        # Cache for future use
        ICD10Code.objects.create(
            code=code,
            description=umls_result["description"],
        )
        return {**umls_result, "source": "umls_api_cached"}
    
    # 3. Not found - flag for review
    return {
        "code": code,
        "description": None,
        "source": "not_found",
        "needs_review": True,
    }
```

---

## 🚀 **Quick Setup: UMLS + Local Cache**

### Step 1: Register for UMLS API (5 minutes)
```bash
# Go to https://www.nlm.nih.gov/research/umls/
# Click "Request a License"
# Instant approval
# Copy API key
```

### Step 2: Set Environment Variable
```bash
# In .env or settings.py
UMLS_API_KEY=your_key_here
```

### Step 3: Add Django Model for Caching
```python
# In coding/models.py

class ICD10Code(models.Model):
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField()
    source = models.CharField(max_length=50)  # 'umls', 'cms', etc
    cached_at = models.DateTimeField(auto_now=True)

class CPTCode(models.Model):
    code = models.CharField(max_length=5, unique=True)
    description = models.TextField()
    source = models.CharField(max_length=50)
    cached_at = models.DateTimeField(auto_now=True)
```

### Step 4: Integrate in Validation
```python
# In coding/validation.py

from coding.umls_integration import UMLSCodeLookup
from coding.models import ICD10Code, CPTCode

class DatabaseCodingValidator:
    def validate_code(self, system: str, code: str):
        """Enhanced validation using APIs."""
        
        if system == "ICD10":
            # Try local first
            existing = ICD10Code.objects.filter(code=code).first()
            if existing:
                return (True, None, existing.description)
            
            # Try UMLS
            umls_result = UMLSCodeLookup.get_icd10_info(code)
            if umls_result:
                # Cache it
                ICD10Code.objects.create(
                    code=code,
                    description=umls_result["description"],
                    source="umls",
                )
                return (True, None, umls_result["description"])
            
            # Not found
            return (False, f"Code {code} not found in UMLS", None)
```

---

## 💰 **Cost Comparison**

| Option | Setup | Annual | Speed | Accuracy |
|--------|-------|--------|-------|----------|
| **UMLS** | 5 min | $0 | Medium | ⭐⭐⭐⭐⭐ |
| **CMS Files** | 30 min | $0 | Fast | ⭐⭐⭐⭐⭐ |
| **AMA CPT** | 1 day | $500+ | Medium | ⭐⭐⭐⭐⭐ |
| **Your CSV** | Done | $0 | Fastest | ⭐⭐ (broken) |

---

## ✅ **Recommended for Your Project**

**Use:** UMLS API + Local Cache (Django DB)

**Why:**
1. Free forever ✓
2. Authoritative (NIH) ✓
3. Real-time updates ✓
4. Can validate all LLM-generated codes ✓
5. No licensing restrictions ✓
6. Instant registration ✓

**Files provided:**
- `coding/umls_integration.py` - Ready to use
- Just add environment variable: `UMLS_API_KEY`
- Add Django models for caching
- Replace CSV validation with API calls

---

## 📝 **Next Steps**

1. **Register for UMLS:** https://www.nlm.nih.gov/research/umls/ (instant)
2. **Install:** `pip install requests`
3. **Add models** to `coding/models.py`
4. **Update validation.py** to use `UMLSCodeLookup`
5. **Test:** Query N18.31 and other missing codes
6. **Remove:** Old CSV files

Your system will then have:
- ✅ All ICD-10 stage codes (N18.31, N18.32, etc.)
- ✅ Correct descriptions (no truncation)
- ✅ Real-time code validation
- ✅ No broken Z79 codes
- ✅ Zero licensing cost
