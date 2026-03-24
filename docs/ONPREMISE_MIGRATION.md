# Zep Cloud → 완전 온프레미스 전환 가이드

## 1. 배경 및 목적

현재 MiroFish는 지식 그래프와 에이전트 기억 관리를 **Zep Cloud**(외부 SaaS)에 의존합니다. 이는 다음 문제를 야기합니다:

- **데이터 보안**: 수요기관의 마케팅 데이터, 민감 정보가 외부 클라우드로 전송
- **네트워크 의존**: 인터넷 연결 필수, 오프라인 환경 불가
- **비용**: Zep Cloud 유료 플랜 필요 (대규모 사용 시)
- **지연시간**: 클라우드 API 호출 레이턴시

**목표**: Zep Cloud를 **Graphiti + Neo4j + 로컬 임베딩 모델**로 대체하여 완전 온프레미스 환경 구축

## 2. 현재 Zep Cloud 의존성

### 2.1 사용 SDK

- `zep-cloud==3.13.0` (Python)
- 클라이언트: `from zep_cloud.client import Zep`
- API 엔드포인트: `https://api.zep.cloud` (하드코딩, 변경 불가)

### 2.2 영향 파일 (6개)

| 파일 | 역할 | Zep API 호출 |
|------|------|-------------|
| `graph_builder.py` | 그래프 생성/온톨로지/데이터 추가 | create, set_ontology, add_batch, episode.get, delete |
| `zep_tools.py` | 검색/노드·엣지 조회 | graph.search, node.get, fetch_all |
| `zep_entity_reader.py` | 엔티티 필터링/조회 | node.get, get_entity_edges, fetch_all |
| `zep_graph_memory_updater.py` | 시뮬레이션 기억 저장 | graph.add |
| `zep_paging.py` | 페이지네이션 유틸 | node.get_by_graph_id, edge.get_by_graph_id |
| `oasis_profile_generator.py` | Zep 클라이언트 초기화 | (초기화만) |

### 2.3 Zep이 내부적으로 처리하는 기능

| 기능 | 설명 | 대체 필요 |
|------|------|----------|
| **임베딩 생성** | 텍스트→벡터 변환 (검색용) | 로컬 임베딩 모델 필요 |
| **NER/RE 추출** | 텍스트→엔티티/관계 자동 추출 | Graphiti가 LLM으로 처리 |
| **시맨틱 검색** | 벡터 유사도 + BM25 하이브리드 | Graphiti search API |
| **크로스인코더 리랭킹** | 검색 결과 정밀도 향상 | Graphiti 또는 자체 구현 |

## 3. 대체 아키텍처

### 3.1 기술 스택

```
현재 (Zep Cloud):
  MiroFish Backend → [인터넷] → Zep Cloud API → (내부 Neo4j + 임베딩)

전환 후 (온프레미스):
  MiroFish Backend → [로컬 네트워크] → Graphiti Server → Neo4j (로컬)
                                         ↓
                                    로컬 임베딩 모델 (vLLM/TEI)
                                         ↓
                                    로컬 LLM (Qwen3-32B, NER/RE용)
```

### 3.2 구성요소

| 구성요소 | 기술 | 배포 | 리소스 |
|----------|------|------|--------|
| 그래프 DB | Neo4j 5.26+ Community | Docker (gpu-svr1) | 4GB RAM, 20GB 디스크 |
| 그래프 엔진 | Graphiti Server | Docker (gpu-svr1) | 2GB RAM |
| 임베딩 모델 | intfloat/multilingual-e5-large | vLLM 또는 TEI (gpu-svr1 GPU #1) | ~2GB VRAM |
| LLM (NER/RE) | Qwen3-32B | 기존 vLLM 서버 | 기존 GPU #0 활용 |

### 3.3 선례: MiroFish-Offline

[MiroFish-Offline](https://github.com/nikmcfly/MiroFish-Offline)이 이미 구현한 것:
- `GraphStorage` 추상 인터페이스 → Neo4j 구현체
- LLM 기반 동기식 NER/RE (Zep 비동기 에피소드 대체)
- Ollama 로컬 스택

## 4. 구현 계획

### Phase 1: 인프라 배포

#### 4.1.1 Neo4j Docker 배포

```bash
# gpu-svr1에서 실행
docker run -d \
  --name neo4j \
  --restart unless-stopped \
  -p 7474:7474 -p 7687:7687 \
  -v $HOME/neo4j/data:/data \
  -v $HOME/neo4j/logs:/logs \
  -e NEO4J_AUTH=neo4j/mirofish2026 \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5.26-community
```

#### 4.1.2 Graphiti Server 배포

```bash
docker run -d \
  --name graphiti \
  --restart unless-stopped \
  -p 8002:8000 \
  -e NEO4J_URI=bolt://neo4j:7687 \
  -e NEO4J_USER=neo4j \
  -e NEO4J_PASSWORD=mirofish2026 \
  -e OPENAI_API_KEY=dummy \
  -e OPENAI_BASE_URL=http://host.docker.internal:8001/v1 \
  --link neo4j \
  zepai/graphiti:latest
```

#### 4.1.3 임베딩 모델 서빙

```bash
# H100 GPU #1에서 임베딩 전용 서빙
~/vllm-env/bin/python -m vllm.entrypoints.openai.api_server \
  --model intfloat/multilingual-e5-large \
  --port 8002 \
  --host 0.0.0.0 \
  --task embedding
```

또는 Hugging Face TEI (Text Embeddings Inference):
```bash
docker run -d --gpus '"device=1"' \
  -p 8002:80 \
  ghcr.io/huggingface/text-embeddings-inference:latest \
  --model-id intfloat/multilingual-e5-large
```

### Phase 2: 어댑터 레이어 구현

#### 4.2.1 추상 인터페이스 (`graph_storage.py`)

```python
class GraphStorage(ABC):
    @abstractmethod
    def create_graph(self, graph_id, name, description) -> str: ...
    @abstractmethod
    def delete_graph(self, graph_id) -> None: ...
    @abstractmethod
    def set_ontology(self, graph_id, ontology) -> None: ...
    @abstractmethod
    def add_episodes(self, graph_id, episodes) -> list: ...
    @abstractmethod
    def search(self, graph_id, query, limit) -> list: ...
    @abstractmethod
    def get_all_nodes(self, graph_id) -> list: ...
    @abstractmethod
    def get_all_edges(self, graph_id) -> list: ...
    @abstractmethod
    def get_node(self, graph_id, node_uuid) -> dict: ...
    @abstractmethod
    def get_node_edges(self, graph_id, node_uuid) -> list: ...
    @abstractmethod
    def add_memory(self, graph_id, text) -> None: ...
```

#### 4.2.2 Zep 구현체 (`graph_storage_zep.py`) — 기존 코드 래핑

기존 `zep-cloud` 코드를 추상 인터페이스에 맞게 래핑. 기존 동작 유지.

#### 4.2.3 Graphiti 구현체 (`graph_storage_graphiti.py`)

Graphiti REST API를 추상 인터페이스에 맞게 구현.

#### 4.2.4 설정 기반 전환

```python
# config.py
GRAPH_BACKEND = os.environ.get('GRAPH_BACKEND', 'zep')  # 'zep' | 'graphiti'
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', '')
GRAPHITI_URL = os.environ.get('GRAPHITI_URL', 'http://localhost:8002')
EMBEDDING_API_URL = os.environ.get('EMBEDDING_API_URL', '')
```

`.env` 설정만으로 Zep Cloud ↔ Graphiti 전환 가능.

### Phase 3: 서비스 파일 수정

| 파일 | 변경 내용 |
|------|----------|
| `graph_builder.py` | `Zep` 직접 호출 → `GraphStorage` 인터페이스 사용 |
| `zep_tools.py` | `Zep` 직접 호출 → `GraphStorage.search()` 등 사용 |
| `zep_entity_reader.py` | `Zep` 직접 호출 → `GraphStorage.get_all_nodes()` 등 사용 |
| `zep_graph_memory_updater.py` | `Zep` 직접 호출 → `GraphStorage.add_memory()` 사용 |
| `zep_paging.py` | Graphiti용 페이지네이션 추가 (또는 불필요) |
| `config.py` | 새 환경 변수 추가 |

### Phase 4: 테스트

1. Zep 백엔드(`GRAPH_BACKEND=zep`): 기존 동작 회귀 테스트
2. Graphiti 백엔드(`GRAPH_BACKEND=graphiti`): 전체 파이프라인 테스트
3. 오프라인 테스트: 외부 네트워크 차단 후 동작 확인
4. 성능 비교: Zep Cloud vs 로컬 Graphiti 레이턴시/처리량

## 5. 환경 변수 설정 예시

### Zep Cloud (기존, 기본값)
```env
GRAPH_BACKEND=zep
ZEP_API_KEY=z_xxxx
```

### Graphiti + Neo4j (온프레미스)
```env
GRAPH_BACKEND=graphiti
GRAPHITI_URL=http://192.168.0.150:8002
NEO4J_URI=bolt://192.168.0.150:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mirofish2026
EMBEDDING_API_URL=http://192.168.0.150:8003/v1
```

## 6. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Graphiti API ≠ Zep Cloud API | 어댑터 개발 필요 | 추상 인터페이스로 차이 흡수 |
| NER/RE 품질 차이 | 엔티티 추출 정확도 변동 | Qwen3-32B의 NER 성능 검증 |
| 임베딩 모델 품질 | 검색 정확도 변동 | multilingual-e5-large로 다국어 지원 |
| Neo4j 운영 부담 | DB 관리 필요 | Docker + 자동 백업 스크립트 |
| 디스크 사용량 증가 | 그래프 데이터 로컬 저장 | /home 1.7TB 여유 (충분) |

## 7. 예상 리소스

| 항목 | 사양 |
|------|------|
| Neo4j | Docker, 4GB RAM, 20GB 디스크 |
| Graphiti | Docker, 2GB RAM |
| 임베딩 모델 | GPU #1, ~2GB VRAM |
| 추가 디스크 | ~30GB |
| 개발 기간 | 2-3일 |
