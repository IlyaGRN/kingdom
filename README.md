# Machiavelli's Kingdom

A medieval strategy board game for 4-6 players, playable in the browser with AI opponents powered by multiple LLM providers.

## Features

- **Human vs AI** - Play against AI opponents powered by OpenAI GPT-4, Anthropic Claude, Google Gemini, or xAI Grok
- **AI Simulation Mode** - Watch AI players compete against each other with configurable speed
- **Full Game Rules** - Implements V2 rules including combat, titles, alliances, and prestige scoring
- **Interactive Board** - Click-based interface with the original board design overlay

## Tech Stack

### Backend (Python)
- **FastAPI** - Async web framework with WebSocket support
- **Pydantic** - Type-safe data validation
- **OpenAI/Anthropic/Google/xAI SDKs** - AI player integrations

### Frontend (TypeScript)
- **React 18** - Component-based UI
- **Vite** - Fast build tooling
- **Tailwind CSS** - Utility-first styling
- **Zustand** - Lightweight state management
- **React Query** - API state management

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The game will be available at http://localhost:5173

### Environment Variables

Create a `.env` file in the `backend` directory:

```env
# Required for AI players (at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
XAI_API_KEY=...

# Optional
DATABASE_URL=sqlite:///./kingdom.db
DEBUG=true
```

If API keys are not provided, the game will use a simple rule-based AI as a fallback.

## Game Rules Summary

### Objective
Gain the most Prestige Points (VP) by conquering towns, claiming titles, and holding the crown.

### Titles
- **Baron** - Starting rank
- **Count** - Own 2/3 towns in a county (25 Gold)
- **Duke** - Be Count + own 1 town in adjacent county (50 Gold)
- **King** - Be Duke + Count in other duchy (75 Gold)

### Combat
- Commit minimum 200 soldiers
- Roll 2d6 + (soldiers/100) + modifiers
- Winner loses half soldiers, loser loses all
- Defender wins ties

### Scoring
| Holding | VP |
|---------|-----|
| Town | 1 |
| County | +2 |
| Duchy | +4 |
| King | +6 |
| Per round as King | +2 |

### Game Length
- 4 players: 10 rounds (~90 min)
- 5 players: 11 rounds (~105 min)
- 6 players: 12 rounds (~120 min)

## Project Structure

```
kingdom/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── config.py        # Configuration
│   │   ├── api/
│   │   │   ├── routes.py    # REST endpoints
│   │   │   └── websocket.py # WebSocket handlers
│   │   ├── game/
│   │   │   ├── engine.py    # Game logic orchestration
│   │   │   ├── state.py     # State management
│   │   │   ├── combat.py    # Combat resolution
│   │   │   ├── cards.py     # Card deck
│   │   │   └── board.py     # Board topology
│   │   ├── ai/
│   │   │   ├── base.py      # AI player interface
│   │   │   ├── manager.py   # AI orchestration
│   │   │   └── *_player.py  # Provider implementations
│   │   └── models/
│   │       └── schemas.py   # Pydantic models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── store/           # Zustand store
│   │   ├── api/             # API client
│   │   └── types/           # TypeScript types
│   ├── public/
│   │   └── board.png        # Game board image
│   └── package.json
└── README.md
```

## API Endpoints

### Game Management
- `POST /api/games` - Create new game
- `GET /api/games/{id}` - Get game state
- `POST /api/games/{id}/start` - Start game
- `POST /api/games/{id}/action` - Perform action
- `GET /api/games/{id}/valid-actions/{player_id}` - Get valid actions

### Simulation
- `POST /api/simulation/create` - Create AI-only simulation
- `POST /api/simulation/{id}/step` - Execute one turn
- `POST /api/simulation/{id}/run` - Run full simulation

### WebSocket
- `ws://localhost:8000/ws/game/{id}` - Real-time game updates
- `ws://localhost:8000/ws/simulation/{id}` - Watch simulation

## Development

### Running Tests

```bash
cd backend
pytest
```

### Building for Production

```bash
# Frontend
cd frontend
npm run build

# Backend - use gunicorn or similar
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Future Enhancements (Stage 2)

- [ ] Multiplayer via WebSocket rooms
- [ ] User accounts and game history
- [ ] Persistent database storage
- [ ] Replay system
- [ ] Mobile-responsive design

## License

MIT

## Credits

Game design based on "Machiavelli's Kingdom" Rules V2.

