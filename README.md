# SmartCart AI

## System Architecture

<img width="1672" height="941" alt="SmartCart AI System Architecture" src="https://github.com/user-attachments/assets/67b762a2-8996-4b06-9e18-177d590b620d" />

---

## Overview

SmartCart AI A complete project built on the Retailrocket (2015) dataset. It began with recommendation and churn notebooks using classical machine learning and evolved into an application with a backend, frontend, secure accounts, a chatbot, and an admin analytics dashboard.

The project has two tracks: Recommendation, which suggests products to each visitor, and Churn Prediction, which identifies previous purchasers who may become inactive for 30 days.

Project stages, in order:

1. Notebooks التوصية والـ Churn (الأجزاء A وB على Kaggle).
2. تصدير للـ RAG والـ agents (الجزء C) وطبقة المنتجات المولّدة (الجزء D).
3. قاعدة بيانات e-commerce من الداتا الحقيقية.
4. MLflow وتصدير الـ 18 موديل.
5. الـ API وخدمة الموديلات، ثم واجهة React.
6. الحسابات والصلاحيات والتوصيات الشخصية والشات بوت وتحليلات الأدمن.
7. Docker وCI والرفع على GitHub.

A consistent rule across all stages: generated content (product names and prices) is marked with `*_is_synthetic`. Figures in this report come from actual runs or project files.

## Data and E-commerce Database

The source is the Retailrocket dataset on Kaggle. A relational SQLite database of approximately 697 MB was built from it, with `schema.sql` for migration to PostgreSQL. The run on the real dataset completed without errors, and all six checks passed.

### Dataset Size (from the Actual Kaggle Run)

| الجدول | العدد |
| --- | --- |
| events (بعد حذف التكرار) | 2,755,641 |
| customers | 1,407,580 (منهم 11,719 اشتروا) |
| products | 235,061 |
| categories | 1,669 |
| sessions | 1,761,675 |
| orders | 17,672 (فيهم 22,457 صنف) |

الجداول: `products`, `categories`, `customers`, `customer_features`, `sessions`, `events`, `orders`, `order_items`, `cart_items`, `daily_stats`, `db_info` + ثلاث views.

### Real vs. Synthetic Data

| النوع | المحتوى |
| --- | --- |
| حقيقي | الأحداث (view وaddtocart وtransaction)، الـ ids، التواريخ، أرقام الـ transactions، شجرة الأقسام، وحالة المخزون `in_stock` (من خاصية `available`) |
| متحسب من الأحداث الحقيقية | الـ sessions (فاصل 30 دقيقة)، الـ orders والـ carts، عدّادات التحويل، مميزات العميل (آخر نشاط، التكرار، ترك السلة، القسم المفضل، شريحة بقاعدة بسيطة) |
| مولّد من الـ id | اسم المنتج والماركة والسعر وفئة السعر وعلامة العرض (deal) وأسماء الأقسام. وكل رقم مبني على الأسعار (قيمة الأوردر، صرف العميل، الإيراد) مولّد كمان |

### How Product Names and Prices Were Generated

مولّد محدّد (deterministic) مبني على hash للـ id مع seed ثابت (`20150503`)، فنفس المنتج يطلع بنفس الاسم والسعر في كل تشغيل، والـ ids بتفضل متوافقة مع الداتا الحقيقية.

- اسم المنتج = ماركة + نوع + حرفين + الـ id، فالأسماء فريدة.
- السعر = سعر أساسي للنوع × معامل القسم × معامل الماركة × عامل عشوائي لوغاريتمي لكل منتج، مقرّب لأسعار التجزئة.
- فئة السعر (budget وstandard وpremium) ثلثات داخل كل نوع، والـ deal خصم 30%.
- الأقسام اتوزّعت بالتناوب على جذور الشجرة عشان ما يبقاش فيه قسم ناقص.

### Observations from the Actual Run

- المخزون: 22.5% من المنتجات متاحة، و`in_stock` فاضي (NULL) لبعض المنتجات اللي ملهاش سجل `available`، ولازم يتعامل معاه كـ "غير معروف".
- التصنيف: 78.8% من المنتجات ليها قسم في الشجرة، والباقي بياخد قسم تقريبي مولّد.
- الشرائح: حوالي 97% من العملاء شريحة `browser` (شافوا وماشتروش)، وهو طبيعي في داتا زي دي.
- ترك السلة: 69.3% من الأصناف اللي اتضافت للسلة مااتشترتش.

### Passed Data Checks

Row counts match the source, foreign keys are valid, event and order totals reconcile, joins using the original IDs match 100%, product names are unique, and prices are positive.

## Recommendation System

Recommendations use two stages: candidates are gathered from multiple sources, then reranked by a trained model. This is Part A (sections 1–23) of `smartcart_final_recommendation.ipynb`.

### Setup

- الـ session = نشاط زائر بفاصل 30 دقيقة.
- السؤال لكل زيارة: بعد أول 3 أحداث، إيه المنتجات اللي هتتشترى في نفس الزيارة (الـ truth).
- مهمتان: **purchase** (التنبؤ بالشراء بما فيه المنتجات اللي شافها قبل كده) و**discovery** (منتجات جديدة مالمسهاش الزائر قبل كده).

### Stage 1: Candidate Generation

Four sources are combined using reciprocal rank fusion (RRF):

- `ctx`: منتجات من سياق الزيارة الحالية.
- `cf`: تشابه بين المنتجات (collaborative filtering).
- `pop`: الأكثر شعبية.
- `catpop`: الأكثر شعبية داخل أقسام الزائر.

### Stage 2: Reranking

خمسة rankers اتقارنوا على نفس المرشحات، مع مجموعتين (ensembles): أعلى 3 وكل الخمسة. مميزات الـ purchase هي 38 (سياق الزيارة `q_`، إحصائيات المنتج `i_`، علاقة الزائر بالمنتج `p_`، ترتيب المصادر `rr_` و`score_`، وعدد المصادر والـ RRF)، والـ discovery على 31 ميزة.

### Results (NDCG@10, from the Kaggle Run)

| الموديل | purchase validation | purchase test | discovery validation | discovery test | الإعدادات |
| --- | --- | --- | --- | --- | --- |
| Logistic Regression | 0.682 | 0.675 | 0.061 | 0.043 | C = 0.01 |
| Random Forest | 0.688 | 0.677 | 0.042 | 0.034 | max\_depth 10، min\_samples\_leaf 20 |
| XGBoost Ranker | 0.687 | 0.678 | 0.061 | 0.038 | max\_depth 3، 400 trees |
| LightGBM Ranker | 0.689 | 0.675 | 0.056 | 0.031 | 200 trees، 15 leaves |
| HistGradientBoosting | 0.686 | 0.675 | 0.049 | 0.036 | max\_depth 3، 300 iterations |

The final model is selected using validation: **LightGBM** for purchase and **Logistic Regression** for discovery.

### Results Interpretation

- في الـ purchase الفرق بين الموديلات في الخانة العشرية الثالثة، لأن النتيجة مسيطر عليها إعادة التفاعل مع منتجات الزيارة نفسها: السياق لوحده وصل لحوالي 0.665، والـ ML ضاف حوالي 0.005 بس (معنوي بالكاد).
- في الـ discovery المهمة أصعب بكتير (NDCG حوالي 0.04)، لكن الـ ML هنا فيه مكسب حقيقي على الترتيب بدونه.
- الموديل الأبسط (Logistic Regression) هو الأفضل في الـ discovery، وهو الأعلى كمان على الـ test (0.043)، بينما XGBoost وصل لنفس الـ validation (0.061) ونزل على الـ test (0.038).

## Churn Prediction

Churn is Part B (sections 24–35). The final model is calibrated logistic regression, which clearly outperforms the “last activity only” baseline.

### Definition and Methodology

- المجموعة: العملاء اللي اشتروا قبل نقطة القطع، والـ churn = مفيش أي نشاط خلال 30 يوم بعدها. الـ notebook اختار التعريف ده تلقائياً.
- مقياس الاختيار: PR-AUC للفئة اللي هتفضل (retained)، لأن 93% من العملاء بيعملوا churn ومقاييس زي الـ accuracy مابتفرقش.
- مقارنة أربع موديلات (logistic regression وtree وLightGBM وMLP) مع قاعدة بسيطة (آخر نشاط) وتخمين عشوائي.
- معايرة الاحتمالات، وعتبة قرار مبنية على التكلفة والربح، وتقسيم لـ 3 مستويات (tiers)، وتفسير لكل عميل (SHAP وتفسير خطي).

### Test Results

| الموديل | PR-AUC retained | lift مقابل العشوائي | ROC-AUC | Brier |
| --- | --- | --- | --- | --- |
| logistic regression (النهائي) | 0.366 | 5.51 | 0.804 | 0.052 |
| LightGBM | 0.355 | 5.36 | 0.786 | 0.053 |
| MLP | 0.351 | 5.29 | 0.795 | 0.052 |
| tree | 0.328 | 4.94 | 0.776 | 0.053 |
| قاعدة "آخر نشاط فقط" | 0.223 | 3.36 | - | - |
| تخمين عشوائي | 0.066 | 1.00 | - | - |

الموديل النهائي أعلى من العشوائي بحوالي 5.5 مرة، ومن قاعدة آخر نشاط بـ 0.366 مقابل 0.223.

### Threshold and Risk Tiers

- عتبة الـ High = **0.835** (نقطة التعادل التحليلية 0.833، والتجريبية على الـ validation 0.81).
- حد الـ Medium = **0.716**، وحد الـ High الأعلى هو وسيط احتمالات الـ validation فوق العتبة.

| tier | عملاء | نسبة الـ churn الفعلية |
| --- | --- | --- |
| High | 8,507 | 96.1% |
| Medium | 471 | 79.8% |
| Low | 467 | 56.5% |

الترتيب منطقي: كل ما الـ tier أعلى تزيد نسبة الـ churn الفعلية. حجم Medium وLow ناتج من طريقة القطع، مش قرار بيزنس. الـ Medium كان فاضي في أول تشغيل حقيقي، فتم تعديل طريقة حساب الحدود والتشغيل التاني أظهر الـ tiers الثلاثة.

### Business Decision

- الربح مع العتبة: 6,533 مقابل 5,683 لو اتواصل مع الكل، يعني حوالي +15%، لأن 93% من العملاء بيعملوا churn أصلاً.
- أعلى 10% بالمخاطرة (945 عميل) ربحهم المحقق 867، يعني حوالي 0.92 لكل عميل مقابل 0.60 لو اتواصل مع الكل.

### Safety Checks

- النوافذ الزمنية منفصلة والـ features مابتشوفش المستقبل.
- اختبار الـ labels المخلوطة: 0.089 مقابل نسبة أساس 0.083، فمفيش تسريب.
- 45.1% من عملاء الـ test ظاهرين كمان في الـ train. مش تسريب لأن الـ labels في فترة تانية، لكن الأرقام ممكن تكون أحسن شوية من الواقع.

## MLflow and Model Export

اتسجّلت 18 تجربة موديل في MLflow على Kaggle (experiment اسمه `SmartCart-RetailRocket`)، واتصدّرت الموديلات كلها كملفات joblib مع قائمة الـ features والـ config.

| المجموعة | العدد | التفاصيل |
| --- | --- | --- |
| purchase rankers | 5 | Logistic Regression وRandom Forest وXGBoost وLightGBM وHistGradientBoosting |
| discovery rankers | 5 | نفس الخمسة |
| churn | 8 | أربعة موديلات (logreg وtree وLightGBM وMLP)، كل واحد خام ومعايَر |

المخرجات في مجلد `models/` في المشروع:

- `models/models/`: 18 ملف joblib مع 18 ملف json (الـ features والإعدادات).
- `churn_all_models_bundle.joblib` و`model_manifest.json` و`recommendation_config.json`.
- ملفات المقاييس: `recommendation_model_metrics.csv` و`churn_test_metrics.csv` و`churn_validation_metrics.csv` و`churn_budget_policy_comparison.csv`.
- `environment.json`: نسخ المكتبات اللي اتدرّبت بيها (scikit-learn 1.6.1 وnumpy 2.1.3 وpandas 2.3.3 وMLflow 3.17.2).
- `mlflow.db` (SQLite) للـ runs والـ metrics والـ params.

ملاحظات مهمة:

- الـ Model Registry فاضي (مفيش موديلات مسجّلة باسم ونسخة)، والموديلات بتتحمّل من ملفات joblib مباشرة.
- مسارات الـ artifacts اتسجّلت على Kaggle (`/kaggle/working/...`)، فعلى جهازك الـ runs والـ metrics بتظهر عادي، وملفات الموديل نفسها بتاخدها من `models/models/`.
- لشغّل الـ UI استخدم نفس إصدار MLflow اللي كتب الملف (3.17.2): `mlflow ui --backend-store-uri sqlite:///models/mlflow.db --port 5000`.

## Application: Backend, Model Serving, and Frontend

The exported models are loaded into FastAPI and run against the real database. The React interface displays products, recommendations, and churn results.

### Backend

- **المكوّنات:** FastAPI مع طبقة قاعدة بيانات تشتغل على SQLite أو PostgreSQL، وتحميل الموديلات عند بداية التشغيل.
- **جداول الخدمة:** `scripts/build_serving_tables.py` بيضيف `item_neighbors` (1,278,143 صف) و`item_popularity` (112,202 صف)، وتشغيله على جهازك اخد 19.5 ثانية. `build_ranker_state.py` بيضيف جداول `rk_*` اللي الـ rankers محتاجينها.
- **التوصيات:** المرشحات ثم الـ ranker النهائي. مميزات الـ ranker بتتبنى وقت الطلب من آخر زيارة (آخر 3 أحداث) وآخر 30 يوم. بمقارنة مع خط الـ notebook على 60 طلب اختبار، 36 من 38 ميزة متطابقة، والاتنتين اللي باقيين (ترتيب الـ CF والدرجة المدمجة) بتختلف شوية عند تساوي الدرجات.
- **الـ Churn:** نفس الموديل المصدّر (logreg، العتبة 0.835) مع المميزات متبنية من جدول الـ events، للعملاء اللي اشتروا قبل كده فقط.
- **الأداء:** على قاعدة اصطناعية بحجم الحقيقية (211 ألف منتج وْ 2.7 مليون event) كل endpoint رد في أقل من ثانية.
- **PostgreSQL:** النقل والقراءة اتجربوا من الأول للآخر على نفس القاعدة الاصطناعية الكبيرة (النقل اخد 173 ثانية)، والنتايج متطابقة مع SQLite، وكل الاختبارات عدّت على الاثنين.

### Frontend

React + Vite, with pages divided into three levels:

- **عام:** صفحة ترحيب، المنتجات بالبحث والفلاتر، تفاصيل المنتج مع منتجات شبيهة، تسجيل الدخول والتسجيل.
- **المستخدم:** صفحة التوصيات الشخصية، المساعد الذكي، الملف الشخصي والاهتمامات.
- **الأدمن:** لوحة تحكم فيها نظرة عامة وتحليلات المنتجات والعملاء والحسابات والـ Churn والموديلات والبحث عن عميل وسجل العمليات.

التصميم مستلهم من صورة مرجعية منك (sidebar غامق للأدمن وبانر وصفوف توصيات للمستخدم)، لكن كل رقم فيه حقيقي، واللي مالهاش مصدر في الداتا اتشال أو اتبدل: الإيراد ونسبة التطابق والمشتريات الجديدة والمفضلة وصور المنتجات.

## Authentication, Security, Personalization, Chatbot, and Admin Dashboard

**Authentication and Authorization**

- تسجيل ودخول بكلمات سر مشفرة بـ argon2، وجلسة في cookie من نوع HttpOnly اسمها `sc_session` (المخزن في الداتابيز هو الـ hash فقط).
- حماية CSRF بهيدر `X-CSRF-Token` مع فحص الـ Origin، وحد لعدد المحاولات (rate limit) على الدخول والتسجيل.
- الـ role مش بيتحدد من العميل أبداً (أي محاولة بترجع 422). الـ admin بيتعمل بس من `scripts/create_admin.py`.
- الـ endpoints القديمة الخاصة بالعملاء بقت للـ admin فقط، وربط الحساب بزائر من الداتا ده للـ admin بس.

**Personalization**

- كل تفاعل (مشاهدة، إضافة للسلة) بيتسجل في `interaction_events` مرتبط بالحساب.
- التوصيات بتتبني من آخر 3 أحداث + تاريخ 30 يوم، والـ features بتتحسب وقت الطلب.
- صفحة نشاطي `/me/activity` بتعرض أحداث صاحب الحساب فقط.

**Chatbot**

- The chatbot intents and tools are deterministic: responses come from real API data.
- لو فيه LLM اختياري، دوره إعادة الصياغة بس، وفيه فحص صارم للمخرجات.
- المحادثات مرتبطة بالحساب وتتمسح.
- **مهم:** الـ LLM ما اتجربش مع مزود حقيقي، اتجرب بمزودين وهميين فقط.

**Admin Analytics**

- المنتجات: الأكثر مبيعاً، الأكثر مشاهدة، الأكثر إضافة للسلة، نسبة التحويل (بحد أدنى 100 مشاهدة)، منتجات اتشافت ومتباعتش، وتحليل الأقسام.
- العملاء: المشترون والمتكررون، قمع الجلسات، توزيع الطلبات لكل عميل، الشرائح، آخر ظهور، الساعة واليوم، وأعلى العملاء.
- كلها من جداول وعدادات محسوبة مسبقاً مع cache خمس دقايق.
- صفحات إدارة المستخدمين وسجل التدقيق (Audit) ولوحة الـ Churn والموديلات.

## Testing, CI, and Deployment

**Tests Actually Executed**

- النسخة الأخيرة عندي: 118 اختبار نجحوا على SQLite بالإصدارات المثبتة.
- تشغيل كامل على Postgres: 112 نجحوا، لكن ده كان قبل آخر الاختبارات المضافة (تحليلات المنتجات والعملاء ونشاط المستخدم)، فمحتاج إعادة تشغيل.
- الـ repo بتاعك (بعد تعديلاتك): 133 اختبار نجحوا عندي.
- اتجرب في متصفح حقيقي على نسخة تجريبية من الداتابيز: الدخول، الداشبورد، المنتجات، تحليلات العملاء، والموبايل.

**الـ CI**

- The workflow file is written but has never run on GitHub; the first run may still reveal issues.

**Deployment**

- الخطة المقترحة: VM واحدة على Azure (B2s) بـ docker compose + Caddy للـ HTTPS، والداتا (700 ميجا) تتنقل مضغوطة بـ scp أو Blob، ونسخ احتياطي بـ pg\_dump.
- ملفات الـ Docker ما اتبنتش ولا اتجربت لسه، وملفات الـ production (docker-compose.prod.yml وCaddyfile) لسه ما اتكتبتش.

## Known Limitations and Next Steps

**Limitations to State Clearly**

- The application has no checkout, so it does not record purchases. Sales figures in the dashboards come from the Retailrocket dataset.
- Product names and prices are synthetic, not real.
- The LLM has not been tested with a real provider.
- الـ rate limit في ذاكرة العملية الواحدة، ومش بيفهم الـ proxy (الـ IP).
- رد 409 عند التسجيل بإيميل موجود بيكشف إن الإيميل مسجل.
- The MLflow Model Registry is empty.
- The Kaggle notebooks themselves are not included in the repository.
- الـ Docker build وأول تشغيل للـ CI ما اتجربوش، واختبارات Postgres محتاجة إعادة تشغيل.

**Recommended Next Steps**

1. دمج شغلي الأخير (تحليلات المنتجات والعملاء، واجهة المستخدم v2، الـ README الكامل، Postman) مع تعديلاتك في الـ monitoring والـ LLM.
2. رفع الكود وتأكيد نجاح الـ CI.
3. تجربة `docker compose build` وتشغيل اختبارات Postgres.
4. تجهيز ملفات النشر على Azure.
5. إضافة نوتبوكات Kaggle للـ repo.
