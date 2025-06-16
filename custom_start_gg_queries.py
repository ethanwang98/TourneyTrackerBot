SHOW_SETS_WITH_SEED_QUERY = """query EventSets($eventId: ID!, $page: Int!, $filters: SetFilters!) {
  event(id: $eventId) {
    tournament {
      id
      name
    }
    name
    state
    sets(page: $page, perPage: 18, sortType: STANDARD, filters: $filters) {
      nodes {
        fullRoundText
        games {
          winnerId
          selections {
            selectionValue
            entrant {
              id
            }
          }
        }
        id
        slots {
          standing {
            id
            placement
            stats {
              score {
                value
              }
            }
          }
          entrant {
            id
            name
            initialSeedNum
            participants {
              entrants {
                id
              }
              player {
                id
                gamerTag
                
              }
            }
          }
        }
        phaseGroup {
          id
          phase {
            name
          }
        }
      }
    }
  }
}
"""

SHOW_EVENT_METADATA = """query ($tourneySlug: String!) {
  tournament(slug: $tourneySlug) {
    name
    events {
      id
      slug
      name
      state
    }
  }
}
"""

SHOW_PLAYER_SETS_QUERY = """query Sets($playerId: ID!, $page: Int!, $filters: SetFilters!) {
  player(id: $playerId) {
    id
    sets(perPage: 10, page: $page, filters: $filters) {
      nodes {
        event {
          state
        }
        fullRoundText
        games {
          winnerId
          selections {
            selectionValue
            entrant {
              id
            }
          }
        }
        id
        slots {
          standing {
            id
            placement
            stats {
              score {
                value
              }
            }
          }
          entrant {
            id
            name
            initialSeedNum
            participants {
              entrants {
                id
              }
              player {
                id
                gamerTag
                
              }
            }
          }
        }
        phaseGroup {
          id
          phase {
            name
          }
        }
      }
    }
  }
}
"""