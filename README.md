# 🎮 FIREFIGHT URCW MOBILE

**Tactical Wargame 2D** basé sur Firefight URCW PC  
Développé par **ZYPROZ** | Stack: HTML5 Canvas + Ably + Capacitor

---

## Features

- ⚔️ Combat tactique tour par tour sur grille 14×10
- 🇺🇦 Ukraine vs 🇷🇺 Russie — unités réelles (T-90M, T-72AMT, BMP-1G, Bradley, SSO, VDV)
- 🗺️ Terrain: Herbe, Forêt (couverture), Routes, Bâtiments, Tranchées
- 🎲 Système de dés: ATQ + D6 vs DEF + Couverture terrain
- 📡 Multijoueur en ligne via **Ably Realtime**
- 📱 APK Android via Capacitor + GitHub Actions

## Sprites

Les sprites sont extraits du jeu PC original **Firefight URCW v12.2.0** et encodés en base64 dans `index.html`.

## Setup

### 1. Configurer Ably
Dans `index.html`, ligne ~14:
```js
const ABLY_KEY = 'VOTRE_CLE_ABLY_ICI';
```

### 2. Déployer sur Render
- Créer un service Static Site
- Pointer vers ce repo
- Dossier de build: `.`

### 3. Build APK (auto via GitHub Actions)
Push sur `main` → APK généré dans les Artifacts

## Gameplay

| Action | Coût PA |
|--------|---------|
| Déplacement 1 case | 1 PA (route: 0.5, forêt: 2) |
| Attaque | 3 PA |
| Tour complet | 6 PA |

| Terrain | Couverture | Mouvement |
|---------|-----------|-----------|
| Herbe | 0 | Normal |
| Forêt | +2 | ×2 |
| Route | -1 | ÷2 |
| Bâtiment | +4 | ×2 |
| Tranchée | +3 | Normal |

## Formule de Combat

```
Dégâts = ATQ_attaquant + D6 - DEF_cible - Couverture_terrain
Minimum = 1
```

## Unités

| Unité | Faction | PV | ATQ | DEF | Portée | MOV |
|-------|---------|-----|-----|-----|--------|-----|
| T-90M | 🇷🇺 RU | 10 | 8 | 3 | 3 | 3 |
| BMP-1G | 🇷🇺 RU | 6 | 5 | 1 | 2 | 4 |
| VDV | 🇷🇺 RU | 4 | 4 | 0 | 2 | 3 |
| T-72AMT | 🇺🇦 UA | 9 | 7 | 3 | 3 | 3 |
| Bradley | 🇺🇦 UA | 7 | 6 | 2 | 3 | 4 |
| SSO | 🇺🇦 UA | 4 | 4 | 0 | 2 | 3 |
