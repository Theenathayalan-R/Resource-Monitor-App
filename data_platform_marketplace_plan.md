# Controls Data Platform Marketplace - Comprehensive Implementation Plan

## 1. High Level Design Architecture

### System Overview
The Controls Data Platform Marketplace is a comprehensive self-service portal that enables data discovery, governance, and consumption across the enterprise. Built on modern cloud-native architecture with microservices pattern.

### Core Components
- **Frontend**: Angular 16+ with Angular Material UI
- **Backend**: Java Spring Boot microservices on OpenShift
- **Data Layer**: Apache Iceberg tables on IBM Cloud Object Storage S3
- **Analytics Engine**: Starburst (Trino) for query federation
- **Orchestration**: Apache Airflow for workflows
- **Identity Management**: OAuth2/OIDC SSO integration
- **API Gateway**: Spring Cloud Gateway for unified access

### Key Capabilities
1. **Data Discovery & Cataloging**: Searchable metadata repository with business glossary
2. **Self-Service Analytics**: Embedded Tableau and Starburst Insights
3. **AI-Powered Insights**: Text-to-SQL chatbot with RAG implementation
4. **Consumer Onboarding**: Automated access request and provisioning
5. **Development Environment**: JupyterHub integration for power users
6. **Data Governance**: Quality scorecards and lineage tracking
7. **Access Management**: Role-based permissions and entitlements

## 2. Microservices Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (Spring Cloud Gateway)       │
│                     - Routing, Load Balancing               │
│                     - Authentication/Authorization          │
│                     - Rate Limiting                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼────┐    ┌──────▼──────┐    ┌─────▼──────┐
│Frontend│    │   Identity  │    │  Notification│
│Angular │    │   Service   │    │   Service    │
│   App  │    │(OAuth/OIDC) │    │   (Email/    │
└────────┘    └─────────────┘    │   Slack)     │
                                 └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Core Business Services                   │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│Data Catalog │ Governance  │User Management│ Consumer        │
│Service      │Service      │Service        │Onboarding Svc   │
│- Metadata   │- Quality    │- RBAC         │- Access Requests│
│- Lineage    │- Scorecards │- Permissions  │- Provisioning   │
│- Discovery  │- Compliance │- User Profiles│- API Keys       │
└─────────────┴─────────────┴─────────────┴─────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Integration Services                     │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│Tableau      │Starburst    │JupyterHub   │ AI/ML Insights  │
│Integration  │Integration  │Integration  │ Service         │
│Service      │Service      │Service      │- Text-to-SQL    │
│- Embedding  │- Query Proxy│- Notebook   │- RAG ChatBot    │
│- SSO Bridge │- Metadata   │Management   │- NLP Processing │
└─────────────┴─────────────┴─────────────┴─────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Data & Storage Layer                    │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│Apache       │PostgreSQL   │Redis        │ Vector Database │
│Iceberg      │(Metadata    │(Caching &   │ (ChromaDB for   │
│on IBM S3    │Repository)  │Sessions)    │ RAG Embeddings) │
└─────────────┴─────────────┴─────────────┴─────────────────┘
```

## 3. Technology Stack

### Frontend Technologies
- **Framework**: Angular 16+ with TypeScript
- **UI Library**: Angular Material + Custom Design System
- **State Management**: NgRx for complex state management
- **Testing**: Jest + Cypress for e2e testing
- **Build Tools**: Angular CLI + Webpack

### Backend Technologies
- **Framework**: Java 17 + Spring Boot 3.x + Spring Cloud
- **API Documentation**: OpenAPI 3.0 + Springdoc
- **Database**: PostgreSQL 14+ for metadata, Redis for caching
- **Message Queue**: Apache Kafka for event streaming
- **Security**: Spring Security + OAuth2/OIDC
- **Testing**: JUnit 5 + TestContainers + WireMock

### Infrastructure & DevOps
- **Container Platform**: OpenShift Container Platform
- **Container Registry**: Red Hat Quay
- **CI/CD**: GitLab CI/CD + ArgoCD
- **Monitoring**: Prometheus + Grafana + Jaeger
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)

### Data & Analytics Stack
- **Data Lake**: Apache Iceberg on IBM Cloud Object Storage S3
- **Query Engine**: Starburst (Trino) for federated queries
- **Analytics**: Tableau Server for BI dashboards
- **Notebooks**: JupyterHub with PySpark kernels
- **AI/ML**: OpenAI API + LangChain + ChromaDB for RAG

## 4. Detailed Project Implementation Plan

### Phase 1: Foundation & Core Services (Weeks 1-8)

#### Epic 1.1: Infrastructure Setup & DevOps Pipeline
**Duration**: 2 weeks

**User Stories**:
- **PLAT-001**: As a DevOps engineer, I need OpenShift namespaces configured for dev/test/prod environments
- **PLAT-002**: As a developer, I need CI/CD pipelines configured for automated build/test/deploy
- **PLAT-003**: As a security admin, I need SSL certificates and network policies configured
- **PLAT-004**: As an operations team member, I need monitoring and logging infrastructure setup

**Acceptance Criteria**:
- OpenShift cluster with 3 environments provisioned
- GitLab CI/CD pipelines operational with automated testing
- ArgoCD configured for GitOps deployment
- Prometheus/Grafana monitoring dashboards configured

#### Epic 1.2: Identity & Access Management Foundation
**Duration**: 2 weeks

**User Stories**:
- **IAM-001**: As a system administrator, I need SSO integration with corporate identity provider
- **IAM-002**: As a user, I need to authenticate using my corporate credentials
- **IAM-003**: As a security officer, I need role-based access control implemented
- **IAM-004**: As an API consumer, I need API key management functionality

**Acceptance Criteria**:
- OAuth2/OIDC integration with corporate IdP
- JWT token-based authentication across services
- RBAC with predefined roles (Admin, Data Steward, Consumer, Analyst)
- API gateway with authentication middleware

#### Epic 1.3: Core Backend Services Setup
**Duration**: 3 weeks

**User Stories**:
- **CORE-001**: As a platform architect, I need Spring Boot microservices template configured
- **CORE-002**: As a developer, I need database schemas designed and implemented
- **CORE-003**: As a system integrator, I need Kafka message broker configured
- **CORE-004**: As a data architect, I need connection to Iceberg catalog established

**Acceptance Criteria**:
- 4 core microservices deployed (User Management, Data Catalog, Governance, Consumer Onboarding)
- PostgreSQL schemas for metadata, user management, and workflows
- Kafka topics configured for event-driven communication
- Iceberg catalog integration with metadata extraction capability

#### Epic 1.4: Frontend Foundation
**Duration**: 1 week

**User Stories**:
- **UI-001**: As a frontend developer, I need Angular application scaffolded with routing
- **UI-002**: As a designer, I need design system and UI components library setup
- **UI-003**: As a user, I need responsive navigation and layout structure
- **UI-004**: As a developer, I need authentication guards and interceptors implemented

**Acceptance Criteria**:
- Angular 16+ application with lazy-loaded modules
- Angular Material customized with enterprise branding
- Responsive layout with navigation sidebar
- Authentication flow with token management

### Phase 2: Data Catalog & Discovery (Weeks 9-14)

#### Epic 2.1: Data Catalog Core Features
**Duration**: 3 weeks

**User Stories**:
- **CAT-001**: As a data consumer, I need to search and discover data assets across the platform
- **CAT-002**: As a data steward, I need to manage data asset metadata and descriptions
- **CAT-003**: As a business user, I need a business glossary with searchable terms
- **CAT-004**: As a data owner, I need data lineage visualization for my datasets

**Acceptance Criteria**:
- Full-text search with faceted filtering (data type, domain, owner, tags)
- Metadata management UI with CRUD operations
- Business glossary with hierarchical term relationships
- Interactive data lineage diagrams using D3.js/vis.js

#### Epic 2.2: Metadata Workflow Management
**Duration**: 2 weeks

**User Stories**:
- **WF-001**: As a data steward, I need approval workflows for metadata changes
- **WF-002**: As a reviewer, I need to review and approve/reject metadata updates
- **WF-003**: As a contributor, I need to track the status of my submissions
- **WF-004**: As an administrator, I need to configure workflow rules and assignments

**Acceptance Criteria**:
- Workflow engine with configurable approval chains
- Email notifications for workflow state changes
- Audit trail for all metadata modifications
- Bulk approval capabilities for authorized users

#### Epic 2.3: Advanced Search & Recommendations
**Duration**: 1 week

**User Stories**:
- **SEARCH-001**: As a data analyst, I need intelligent search suggestions and auto-completion
- **SEARCH-002**: As a frequent user, I need personalized data recommendations
- **SEARCH-003**: As a data consumer, I need to save and share search queries
- **SEARCH-004**: As a platform user, I need popular and trending datasets highlighted

**Acceptance Criteria**:
- Elasticsearch-powered search with auto-suggestions
- Machine learning-based recommendation engine
- Saved searches and bookmarking functionality
- Usage analytics and trending content identification

### Phase 3: Self-Service Analytics Integration (Weeks 15-20)

#### Epic 3.1: Tableau Server Integration
**Duration**: 2 weeks

**User Stories**:
- **TAB-001**: As a business analyst, I need to access Tableau dashboards within the platform
- **TAB-002**: As a dashboard creator, I need single sign-on to Tableau Server
- **TAB-003**: As a data consumer, I need to request access to specific dashboards
- **TAB-004**: As an administrator, I need to manage dashboard permissions and visibility

**Acceptance Criteria**:
- Seamless Tableau Server embedding with trusted authentication
- Dashboard catalog with metadata and access controls
- Self-service access request workflow
- Usage tracking and analytics for dashboard consumption

#### Epic 3.2: Starburst Insights Integration
**Duration**: 2 weeks

**User Stories**:
- **STAR-001**: As a data analyst, I need to access Starburst query interface within the platform
- **STAR-002**: As a SQL user, I need to execute ad-hoc queries against data lake
- **STAR-003**: As a data explorer, I need query result export and sharing capabilities
- **STAR-004**: As a platform admin, I need query governance and resource management

**Acceptance Criteria**:
- Starburst UI embedded with SSO integration
- Query builder interface for non-SQL users
- Result set export to CSV/Excel/Parquet formats
- Query history and sharing functionality
- Resource limits and cost management controls

#### Epic 3.3: JupyterHub Integration
**Duration**: 2 weeks

**User Stories**:
- **JUP-001**: As a data scientist, I need access to Jupyter notebooks with PySpark
- **JUP-002**: As a power user, I need pre-configured environments with data access
- **JUP-003**: As a collaborator, I need to share and version control notebooks
- **JUP-004**: As an administrator, I need to manage compute resources and user quotas

**Acceptance Criteria**:
- JupyterHub deployment with customized environments
- Pre-installed libraries (PySpark, Pandas, Scikit-learn, etc.)
- Git integration for notebook version control
- Resource quotas and automatic cleanup policies
- Notebook gallery and template library

### Phase 4: AI-Powered Insights & Chatbot (Weeks 21-26)

#### Epic 4.1: RAG Implementation Foundation
**Duration**: 2 weeks

**User Stories**:
- **RAG-001**: As a system architect, I need vector database setup for embeddings storage
- **RAG-002**: As a data engineer, I need automated embedding generation for catalog content
- **RAG-003**: As a developer, I need RAG pipeline for contextual query processing
- **RAG-004**: As a platform user, I need semantic search across data catalog

**Acceptance Criteria**:
- ChromaDB deployed with high availability configuration
- Automated embedding pipeline using OpenAI/Hugging Face models
- LangChain-based RAG implementation
- Semantic similarity search with relevance scoring

#### Epic 4.2: Text-to-SQL Chatbot Development
**Duration**: 3 weeks

**User Stories**:
- **CHAT-001**: As a business user, I need to ask questions in natural language about data
- **CHAT-002**: As a non-technical user, I need SQL queries generated from my questions
- **CHAT-003**: As a data consumer, I need explanations of query results and insights
- **CHAT-004**: As a user, I need conversational context maintained across interactions

**Acceptance Criteria**:
- Natural language processing for SQL generation
- Integration with Starburst for query execution
- Conversational UI with chat history
- Query explanation and result interpretation
- Fallback mechanisms for complex queries

#### Epic 4.3: Advanced Analytics & Insights
**Duration**: 1 week

**User Stories**:
- **INSIGHT-001**: As a data analyst, I need automated insights generated from data patterns
- **INSIGHT-002**: As a business user, I need plain English explanations of data trends
- **INSIGHT-003**: As a decision maker, I need alerting for significant data changes
- **INSIGHT-004**: As a data consumer, I need suggested follow-up questions and analyses

**Acceptance Criteria**:
- Automated anomaly detection and trend analysis
- Natural language generation for insights explanation
- Configurable alerting system with multiple channels
- Contextual query and analysis suggestions

### Phase 5: Consumer Onboarding & Access Management (Weeks 27-32)

#### Epic 5.1: Self-Service Onboarding Portal
**Duration**: 2 weeks

**User Stories**:
- **ONB-001**: As a new data consumer, I need to register and request data access
- **ONB-002**: As a data product owner, I need to define access policies and requirements
- **ONB-003**: As an approver, I need to review and approve access requests efficiently
- **ONB-004**: As a system administrator, I need automated provisioning workflows

**Acceptance Criteria**:
- Registration form with role-based approval routing
- Data product catalog with access requirements
- Approval dashboard with bulk processing capabilities
- Automated account provisioning and API key generation

#### Epic 5.2: API Access Management
**Duration**: 2 weeks

**User Stories**:
- **API-001**: As a developer, I need API keys for programmatic data access
- **API-002**: As a data owner, I need to monitor API usage and set limits
- **API-003**: As a consumer, I need documentation and testing tools for APIs
- **API-004**: As a security officer, I need API security controls and monitoring

**Acceptance Criteria**:
- API key management with rotation policies
- Usage analytics and rate limiting
- OpenAPI documentation with interactive testing
- Security monitoring and anomaly detection

#### Epic 5.3: Data Feed Access Management
**Duration**: 2 weeks

**User Stories**:
- **FEED-001**: As a data consumer, I need to subscribe to S3 data feeds
- **FEED-002**: As a data provider, I need to publish data feed schedules and schemas
- **FEED-003**: As a subscriber, I need notifications for new data availability
- **FEED-004**: As an administrator, I need to manage data feed access and quotas

**Acceptance Criteria**:
- S3 bucket access provisioning with IAM policies
- Data feed catalog with SLA information
- Event-driven notifications for data updates
- Access monitoring and usage reporting

### Phase 6: Data Governance & Quality (Weeks 33-38)

#### Epic 6.1: Data Quality Framework
**Duration**: 2 weeks

**User Stories**:
- **DQ-001**: As a data steward, I need data quality rules and validation framework
- **DQ-002**: As a data owner, I need quality scorecards for my datasets
- **DQ-003**: As a consumer, I need visibility into data quality metrics
- **DQ-004**: As an analyst, I need trend analysis for data quality over time

**Acceptance Criteria**:
- Configurable data quality rules engine
- Automated quality assessment pipeline
- Interactive quality dashboards and scorecards
- Quality trend analysis and alerting

#### Epic 6.2: Data Model Change Management
**Duration**: 2 weeks

**User Stories**:
- **DM-001**: As a data architect, I need to track schema changes and evolution
- **DM-002**: As a downstream consumer, I need to be notified of breaking changes
- **DM-003**: As a developer, I need impact analysis for proposed changes
- **DM-004**: As a data owner, I need approval workflows for schema modifications

**Acceptance Criteria**:
- Schema versioning and change tracking
- Impact analysis with downstream dependency mapping
- Change notification system with affected user alerts
- Approval workflow for schema changes

#### Epic 6.3: Compliance & Governance Reporting
**Duration**: 2 weeks

**User Stories**:
- **COMP-001**: As a compliance officer, I need data governance reports
- **COMP-002**: As an auditor, I need access logs and data lineage documentation
- **COMP-003**: As a privacy officer, I need PII data identification and tracking
- **COMP-004**: As a data steward, I need policy compliance monitoring

**Acceptance Criteria**:
- Automated governance reporting dashboard
- Comprehensive audit logging and traceability
- PII detection and data classification
- Policy compliance scoring and violations tracking

## 5. Detailed Design Specifications

### 5.1 Phase 1 Detailed Design

#### Infrastructure Architecture
**OpenShift Cluster Configuration**:
- **Development Environment**: 3 worker nodes, 8 vCPU, 32GB RAM each
- **Test Environment**: 3 worker nodes, 16 vCPU, 64GB RAM each  
- **Production Environment**: 5 worker nodes, 32 vCPU, 128GB RAM each

**Network Architecture**:
```yaml
apiVersion: v1
kind: NetworkPolicy
metadata:
  name: data-platform-network-policy
spec:
  podSelector:
    matchLabels:
      app: data-platform
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: data-platform-prod
    ports:
    - protocol: TCP
      port: 8080
```

#### Database Schema Design

**User Management Schema**:
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    department VARCHAR(255),
    role VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Roles and permissions
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB
);

-- User role assignments
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id),
    role_id UUID REFERENCES roles(id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);
```

**Data Catalog Schema**:
```sql
-- Data assets
CREATE TABLE data_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    asset_type VARCHAR(100) NOT NULL, -- TABLE, VIEW, DATASET, API
    schema_name VARCHAR(255),
    table_name VARCHAR(255),
    database_name VARCHAR(255),
    owner_id UUID REFERENCES users(id),
    steward_id UUID REFERENCES users(id),
    domain VARCHAR(255),
    classification VARCHAR(100), -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    tags TEXT[],
    metadata JSONB,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Business glossary
CREATE TABLE business_terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term VARCHAR(255) UNIQUE NOT NULL,
    definition TEXT NOT NULL,
    synonyms TEXT[],
    related_terms UUID[],
    domain VARCHAR(255),
    owner_id UUID REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### API Design Specifications

**User Management Service APIs**:
```yaml
openapi: 3.0.3
info:
  title: User Management Service API
  version: 1.0.0
paths:
  /api/v1/users:
    get:
      summary: Get users with pagination and filtering
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 0
        - name: size
          in: query
          schema:
            type: integer
            default: 20
        - name: department
          in: query
          schema:
            type: string
        - name: role
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  content:
                    type: array
                    items:
                      $ref: '#/components/schemas/User'
                  totalElements:
                    type: integer
                  totalPages:
                    type: integer
```

### 5.2 Phase 2 Detailed Design

#### Data Catalog Service Architecture
```java
@RestController
@RequestMapping("/api/v1/catalog")
@CrossOrigin
@Validated
public class DataCatalogController {
    
    @Autowired
    private DataCatalogService catalogService;
    
    @GetMapping("/search")
    public ResponseEntity<SearchResultsDto> searchDataAssets(
            @RequestParam(required = false) String query,
            @RequestParam(required = false) List<String> domains,
            @RequestParam(required = false) List<String> assetTypes,
            @RequestParam(required = false) List<String> classifications,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        SearchCriteria criteria = SearchCriteria.builder()
            .query(query)
            .domains(domains)
            .assetTypes(assetTypes)
            .classifications(classifications)
            .build();
            
        SearchResultsDto results = catalogService.searchAssets(criteria, page, size);
        return ResponseEntity.ok(results);
    }
}

@Service
@Transactional
public class DataCatalogService {
    
    @Autowired
    private ElasticsearchClient elasticsearchClient;
    
    @Autowired
    private DataAssetRepository dataAssetRepository;
    
    public SearchResultsDto searchAssets(SearchCriteria criteria, int page, int size) {
        // Elasticsearch query construction
        SearchRequest request = SearchRequest.of(s -> s
            .index("data_assets")
            .query(q -> q
                .bool(b -> {
                    if (criteria.getQuery() != null) {
                        b.must(m -> m.multiMatch(mm -> mm
                            .query(criteria.getQuery())
                            .fields("name^2", "description", "tags", "domain")));
                    }
                    
                    if (criteria.getDomains() != null) {
                        b.filter(f -> f.terms(t -> t
                            .field("domain.keyword")
                            .terms(TermsQueryField.of(tf -> tf.value(
                                criteria.getDomains().stream()
                                    .map(FieldValue::of)
                                    .collect(Collectors.toList())
                            )))));
                    }
                    
                    return b;
                })
            )
            .from(page * size)
            .size(size)
        );
        
        // Execute search and transform results
        SearchResponse<DataAssetDocument> response = elasticsearchClient.search(request, DataAssetDocument.class);
        return transformSearchResults(response);
    }
}
```

#### Frontend Components Design

**Search Component (Angular)**:
```typescript
@Component({
  selector: 'app-data-catalog-search',
  templateUrl: './data-catalog-search.component.html',
  styleUrls: ['./data-catalog-search.component.scss']
})
export class DataCatalogSearchComponent implements OnInit, OnDestroy {
  searchForm: FormGroup;
  searchResults$: Observable<SearchResults>;
  facets$: Observable<SearchFacets>;
  loading$ = new BehaviorSubject<boolean>(false);
  
  constructor(
    private fb: FormBuilder,
    private catalogService: DataCatalogService,
    private store: Store<AppState>
  ) {
    this.searchForm = this.fb.group({
      query: [''],
      domains: [[]],
      assetTypes: [[]],
      classifications: [[]]
    });
  }
  
  ngOnInit() {
    this.searchResults$ = this.store.select(selectSearchResults);
    this.facets$ = this.store.select(selectSearchFacets);
    
    // Setup reactive search with debouncing
    this.searchForm.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      takeUntil(this.destroy$)
    ).subscribe(criteria => {
      this.performSearch(criteria);
    });
  }
  
  performSearch(criteria: SearchCriteria) {
    this.loading$.next(true);
    this.store.dispatch(DataCatalogActions.searchAssets({ criteria }));
  }
}
```

### 5.3 Phase 3 Detailed Design

#### Tableau Integration Service
```java
@Service
public class TableauIntegrationService {
    
    @Value("${tableau.server.url}")
    private String tableauServerUrl;
    
    @Value("${tableau.trusted.ip}")
    private String trustedIp;
    
    public String generateTrustedTicket(String username, String siteId) {
        try {
            URL url = new URL(tableauServerUrl + "/trusted");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
            
            String postData = String.format("username=%s&target_site=%s&client_ip=%s",
                URLEncoder.encode(username, StandardCharsets.UTF_8),
                URLEncoder.encode(siteId, StandardCharsets.UTF_8),
                URLEncoder.encode(trustedIp, StandardCharsets.UTF_8)
            );
            
            try (OutputStream os = connection.getOutputStream()) {
                os.write(postData.getBytes(StandardCharsets.UTF_8));
            }
            
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(connection.getInputStream()))) {
                return reader.readLine();
            }
            
        } catch (IOException e) {
            throw new TableauIntegrationException("Failed to generate trusted ticket", e);
        }
    }
}
```

### 5.4 Phase 4 Detailed Design

#### RAG Implementation Architecture
```python
# Vector Database Setup
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import DatabaseLoader

class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
        self.vectorstore = Chroma(
            persist_directory="./chroma_db",
            embedding_function=self.embeddings
        )
        
    def index_catalog_content(self):
        # Load data catalog metadata
        loader = DatabaseLoader(
            connection_string=os.getenv("DATABASE_URL"),
            query="""
            SELECT id, name, display_name, description, tags, domain, 
                   schema_name, table_name, metadata 
            FROM data_assets 
            WHERE status = 'ACTIVE'
            """
        )
        
        documents = loader.load()
        
        # Split documents for better embedding
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        splits = text_splitter.split_documents(documents)
        
        # Create embeddings and store in vector database
        self.vectorstore.add_documents(splits)
        
    def semantic_search(self, query: str, k: int = 5):
        """Perform semantic search across catalog content"""
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        return [(doc, score) for doc, score in results if score > 0.7]
```

#### Text-to-SQL Implementation
```java
@Service
public class TextToSqlService {
    
    @Autowired
    private OpenAIService openAIService;
    
    @Autowired
    private DataCatalogService catalogService;
    
    public SqlQueryResponse generateSqlFromText(String naturalLanguageQuery, String userId) {
        // Get relevant schema context using RAG
        List<DataAsset> relevantTables = catalogService.findRelevantTablesForQuery(naturalLanguageQuery);
        
        String schemaContext = buildSchemaContext(relevantTables);
        
        String prompt = buildPrompt(naturalLanguageQuery, schemaContext);
        
        OpenAIRequest request = OpenAIRequest.builder()
            .model("gpt-4")
            .messages(Arrays.asList(
                new OpenAIMessage("system", SYSTEM_PROMPT),
                new OpenAIMessage("user", prompt)
            ))
            .maxTokens(500)
            .temperature(0.1)
            .build();
            
        OpenAIResponse response = openAIService.createCompletion(request);
        
        String generatedSql = extractSqlFromResponse(response.getChoices().get(0).getMessage().getContent());
        
        // Validate and sanitize SQL
        SqlValidationResult validation = validateSql(generatedSql, relevantTables);
        
        if (!validation.isValid()) {
            throw new InvalidSqlException("Generated SQL failed validation: " + validation.getErrors());
        }
        
        return SqlQueryResponse.builder()
            .originalQuery(naturalLanguageQuery)
            .generatedSql(generatedSql)
            .explanation(generateExplanation(generatedSql, naturalLanguageQuery))
            .relevantTables(relevantTables)
            .build();
    }
    
    private String buildPrompt(String query, String schemaContext) {
        return String.format("""
            Given the following database schema context:
            %s
            
            Convert this natural language question to SQL:
            "%s"
            
            Requirements:
            - Generate only valid SQL that works with the provided schema
            - Use appropriate JOINs when multiple tables are involved
            - Include appropriate WHERE clauses for filtering
            - Use proper aggregation functions when needed
            - Limit results to 1000 rows for performance
            
            Return only the SQL query without explanation.
            """, schemaContext, query);
    }
}
```

**Chatbot Frontend Implementation**:
```typescript
@Component({
  selector: 'app-ai-chatbot',
  templateUrl: './ai-chatbot.component.html',
  styleUrls: ['./ai-chatbot.component.scss']
})
export class AiChatbotComponent implements OnInit {
  messages: ChatMessage[] = [];
  messageForm: FormGroup;
  isLoading = false;
  
  constructor(
    private fb: FormBuilder,
    private aiService: AiInsightsService,
    private starburstService: StarburstService
  ) {
    this.messageForm = this.fb.group({
      message: ['', Validators.required]
    });
  }
  
  async sendMessage() {
    if (this.messageForm.invalid || this.isLoading) return;
    
    const userMessage = this.messageForm.value.message;
    this.messages.push({
      id: uuid(),
      content: userMessage,
      sender: 'user',
      timestamp: new Date()
    });
    
    this.isLoading = true;
    this.messageForm.reset();
    
    try {
      // Generate SQL from natural language
      const sqlResponse = await this.aiService.generateSqlFromText(userMessage).toPromise();
      
      // Execute query via Starburst
      const queryResults = await this.starburstService.executeQuery(sqlResponse.generatedSql).toPromise();
      
      // Add bot response with results
      this.messages.push({
        id: uuid(),
        content: this.formatQueryResponse(sqlResponse, queryResults),
        sender: 'bot',
        timestamp: new Date(),
        sqlQuery: sqlResponse.generatedSql,
        queryResults: queryResults.data
      });
      
    } catch (error) {
      this.messages.push({
        id: uuid(),
        content: 'I apologize, but I encountered an error processing your request. Please try rephrasing your question.',
        sender: 'bot',
        timestamp: new Date(),
        isError: true
      });
    } finally {
      this.isLoading = false;
    }
  }
}
```

### 5.5 Phase 5 Detailed Design

#### Consumer Onboarding Workflow
```java
@Entity
@Table(name = "access_requests")
public class AccessRequest {
    @Id
    @GeneratedValue
    private UUID id;
    
    @Column(nullable = false)
    private UUID requesterId;
    
    @Column(nullable = false)
    private String businessJustification;
    
    @ElementCollection
    @Enumerated(EnumType.STRING)
    private Set<DataAssetType> requestedAssetTypes;
    
    @ElementCollection
    private Set<UUID> requestedDataAssets;
    
    @Enumerated(EnumType.STRING)
    private AccessRequestStatus status = AccessRequestStatus.PENDING;
    
    @Column(nullable = false)
    private LocalDateTime requestDate = LocalDateTime.now();
    
    private LocalDateTime approvalDate;
    private UUID approvedBy;
    private String approvalNotes;
    
    // Workflow tracking
    @OneToMany(mappedBy = "accessRequest", cascade = CascadeType.ALL)
    private List<WorkflowStep> workflowSteps = new ArrayList<>();
}

@Service
public class ConsumerOnboardingService {
    
    @Autowired
    private AccessRequestRepository accessRequestRepository;
    
    @Autowired
    private WorkflowEngine workflowEngine;
    
    @Autowired
    private NotificationService notificationService;
    
    @Transactional
    public AccessRequest submitAccessRequest(AccessRequestDto requestDto, String userId) {
        // Validate request
        validateAccessRequest(requestDto);
        
        // Create access request
        AccessRequest request = AccessRequest.builder()
            .requesterId(UUID.fromString(userId))
            .businessJustification(requestDto.getBusinessJustification())
            .requestedAssetTypes(requestDto.getAssetTypes())
            .requestedDataAssets(requestDto.getDataAssets())
            .build();
            
        request = accessRequestRepository.save(request);
        
        // Start approval workflow
        workflowEngine.startWorkflow("data-access-approval", request.getId());
        
        // Send notifications
        notificationService.notifyDataStewards(request);
        
        return request;
    }
    
    @EventListener
    public void handleWorkflowCompletion(WorkflowCompletedEvent event) {
        if ("data-access-approval".equals(event.getWorkflowType())) {
            UUID requestId = event.getEntityId();
            AccessRequest request = accessRequestRepository.findById(requestId)
                .orElseThrow(() -> new EntityNotFoundException("Access request not found"));
                
            if (event.getResult() == WorkflowResult.APPROVED) {
                provisionAccess(request);
            }
            
            notificationService.notifyRequester(request, event.getResult());
        }
    }
    
    private void provisionAccess(AccessRequest request) {
        // Generate API keys
        ApiKey apiKey = apiKeyService.generateApiKey(request.getRequesterId());
        
        // Create IAM policies for S3 access
        iamService.createDataFeedAccessPolicies(request.getRequesterId(), request.getRequestedDataAssets());
        
        // Update user permissions in catalog
        catalogService.grantDataAssetAccess(request.getRequesterId(), request.getRequestedDataAssets());
        
        request.setStatus(AccessRequestStatus.PROVISIONED);
        accessRequestRepository.save(request);
    }
}
```

### 5.6 Phase 6 Detailed Design

#### Data Quality Framework
```java
@Entity
public class DataQualityRule {
    @Id
    @GeneratedValue
    private UUID id;
    
    private String name;
    private String description;
    private UUID dataAssetId;
    private String columnName;
    
    @Enumerated(EnumType.STRING)
    private QualityRuleType ruleType; // COMPLETENESS, VALIDITY, CONSISTENCY, ACCURACY
    
    private String ruleDefinition; // SQL expression or configuration JSON
    private Double threshold; // Minimum passing score
    
    @Enumerated(EnumType.STRING)
    private RuleSeverity severity; // CRITICAL, HIGH, MEDIUM, LOW
    
    private Boolean isActive = true;
    private UUID createdBy;
    private LocalDateTime createdAt = LocalDateTime.now();
}

@Service
public class DataQualityService {
    
    @Autowired
    private StarburstService starburstService;
    
    @Autowired
    private DataQualityRuleRepository ruleRepository;
    
    @Scheduled(cron = "0 0 2 * * *") // Run daily at 2 AM
    public void executeQualityAssessment() {
        List<DataQualityRule> activeRules = ruleRepository.findByIsActiveTrue();
        
        for (DataQualityRule rule : activeRules) {
            try {
                QualityAssessmentResult result = executeQualityRule(rule);
                storeAssessmentResult(result);
                
                if (result.getScore() < rule.getThreshold()) {
                    alertingService.sendQualityAlert(rule, result);
                }
            } catch (Exception e) {
                log.error("Failed to execute quality rule {}: {}", rule.getId(), e.getMessage());
            }
        }
    }
    
    private QualityAssessmentResult executeQualityRule(DataQualityRule rule) {
        String sql = generateQualitySQL(rule);
        QueryResult queryResult = starburstService.executeQuery(sql);
        
        return QualityAssessmentResult.builder()
            .ruleId(rule.getId())
            .executionTime(LocalDateTime.now())
            .score(extractScoreFromResult(queryResult))
            .recordsEvaluated(extractRecordCount(queryResult))
            .failedRecords(extractFailedRecords(queryResult))
            .build();
    }
    
    private String generateQualitySQL(DataQualityRule rule) {
        switch (rule.getRuleType()) {
            case COMPLETENESS:
                return String.format("""
                    SELECT 
                        COUNT(*) as total_records,
                        COUNT(%s) as non_null_records,
                        (COUNT(%s) * 100.0 / COUNT(*)) as completeness_score
                    FROM %s.%s.%s
                    """, 
                    rule.getColumnName(), rule.getColumnName(),
                    rule.getDataAsset().getDatabaseName(),
                    rule.getDataAsset().getSchemaName(),
                    rule.getDataAsset().getTableName()
                );
                
            case VALIDITY:
                return String.format("""
                    SELECT 
                        COUNT(*) as total_records,
                        COUNT(CASE WHEN %s THEN 1 END) as valid_records,
                        (COUNT(CASE WHEN %s THEN 1 END) * 100.0 / COUNT(*)) as validity_score
                    FROM %s.%s.%s
                    """,
                    rule.getRuleDefinition(), rule.getRuleDefinition(),
                    rule.getDataAsset().getDatabaseName(),
                    rule.getDataAsset().getSchemaName(),
                    rule.getDataAsset().getTableName()
                );
                
            default:
                throw new UnsupportedOperationException("Rule type not implemented: " + rule.getRuleType());
        }
    }
}
```

## 6. Requirements Traceability Matrix

| Requirement ID | Description | Epic | User Story | Design Component | Test Case |
|---|---|---|---|---|---|
| **REQ-001** | Data Catalog/Data Dictionary | Epic 2.1 | CAT-001 | DataCatalogService.java | TC-001 |
| **REQ-002** | Business glossary search | Epic 2.1 | CAT-003 | BusinessGlossaryComponent.ts | TC-002 |
| **REQ-003** | Workflow for review/approve | Epic 2.2 | WF-001 | WorkflowEngine.java | TC-003 |
| **REQ-004** | Tableau Server hosting | Epic 3.1 | TAB-001 | TableauIntegrationService.java | TC-004 |
| **REQ-005** | Starburst Insights UI | Epic 3.2 | STAR-001 | StarburstProxyService.java | TC-005 |
| **REQ-006** | Text-to-SQL Chatbot | Epic 4.2 | CHAT-001 | TextToSqlService.java | TC-006 |
| **REQ-007** | RAG Implementation | Epic 4.1 | RAG-001 | RAGService.python | TC-007 |
| **REQ-008** | Consumer Onboarding | Epic 5.1 | ONB-001 | ConsumerOnboardingService.java | TC-008 |
| **REQ-009** | API Access Management | Epic 5.2 | API-001 | ApiKeyManagementService.java | TC-009 |
| **REQ-010** | Data Feeds via S3 | Epic 5.3 | FEED-001 | S3AccessProvisioningService.java | TC-010 |
| **REQ-011** | JupyterHub notebook | Epic 3.3 | JUP-001 | JupyterHubIntegrationService.java | TC-011 |
| **REQ-012** | Data governance | Epic 6.3 | COMP-001 | GovernanceReportingService.java | TC-012 |
| **REQ-013** | Data quality scorecard | Epic 6.1 | DQ-002 | DataQualityService.java | TC-013 |
| **REQ-014** | Data Model changes | Epic 6.2 | DM-001 | SchemaChangeManagementService.java | TC-014 |
| **REQ-015** | Access Management | Epic 1.2 | IAM-003 | UserManagementService.java | TC-015 |

## 7. Devin AI Implementation Strategy

### Devin AI Prompt Templates

#### For Microservice Development:
```
Create a Spring Boot microservice for [SERVICE_NAME] with the following requirements:
- REST API endpoints as specified in the OpenAPI spec
- PostgreSQL integration using JPA/Hibernate
- Redis caching for performance optimization
- Comprehensive error handling and logging
- Unit tests with 80%+ coverage using JUnit 5 and Testcontainers
- Integration tests for API endpoints
- Docker containerization with multi-stage build
- OpenShift deployment manifests
- Monitoring with Micrometer and Prometheus
- Security with JWT token validation

Technical specifications:
- Java 17 + Spring Boot 3.x
- Maven build with standard enterprise plugins
- Follow enterprise coding standards and patterns
- Include comprehensive JavaDoc documentation
```

#### For Angular Frontend Development:
```
Create an Angular component for [COMPONENT_NAME] with the following requirements:
- Responsive design using Angular Material
- Form validation with reactive forms
- State management using NgRx
- Accessibility compliance (WCAG 2.1 AA)
- Internationalization support
- Unit tests with Jest (80%+ coverage)
- E2E tests with Cypress
- Performance optimization with OnPush change detection
- Error handling with user-friendly messages
- Loading states and progress indicators

Technical specifications:
- Angular 16+ with TypeScript 5+
- RxJS for reactive programming
- SCSS for styling with BEM methodology
- Component library following atomic design principles
```

### Development Workflow with Devin AI

1. **Architecture Review**: Devin AI analyzes the high-level design and suggests optimizations
2. **Code Generation**: Automated generation of boilerplate code, tests, and configuration
3. **Quality Assurance**: Automated code review, security scanning, and performance analysis
4. **Testing Strategy**: Comprehensive test suite generation including unit, integration, and E2E tests
5. **Documentation**: Automatic generation of technical documentation, API docs, and deployment guides
6. **DevOps Integration**: CI/CD pipeline configuration and infrastructure as code

### Success Metrics

- **Code Quality**: SonarQube quality gates with 90%+ maintainability rating
- **Test Coverage**: 80%+ code coverage across all services
- **Performance**: API response times < 200ms for 95th percentile
- **Security**: Zero high/critical security vulnerabilities
- **Reliability**: 99.9% uptime SLA for production environment
- **User Adoption**: 80%+ of target users onboarded within 6 months

This comprehensive plan provides Devin AI with detailed specifications to build a robust, scalable, and feature-rich data platform marketplace that meets enterprise standards while delivering exceptional user experience.