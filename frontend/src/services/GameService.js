import axios from 'axios'
import autoBind from 'auto-bind'

const ENDPOINTS = {
  games: '/api/v1/games/',
  played: '/api/v1/games/played/',
  hosted: '/api/v1/games/hosted/',
  other: '/api/v1/games/other/',
  join: '/api/v1/games/{gameId}/join/', // add user to game.wating_room
  gameDetail: '/api/v1/games/:gameId/',

  players: '/api/v1/games/:gameId/players/',
  playersDetail: '/api/v1/games/:gameId/players/:playerId',
  playersMe: '/api/v1/games/:gameId/players/me',
  playersOther: '/api/v1/games/:gameId/players/other',

  actions: '/api/v1/games/:gameId/actions/',
  forceContinue: '/api/v1/games/:gameId/actions/forceContinue/', // mostly for test porpuses
}

export default class GameService {
  constructor(token = null) {
    this.token = token
    autoBind(this)
  }

  get config() {
    return {
      headers: {
        Authorization: `Token ${this.token}`,
      },
    }
  }

  async post(url, data = {}) {
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }
    // for acting actions
    const response = await axios.post(url, data)
    return response.data
  }

  async getAll() {
    const response = await axios.get(ENDPOINTS.games)
    return response.data
  }

  async getPlayed() {}

  async getOther() {}

  async getHosted() {}

  async create() {
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }

    const response = await axios.post(ENDPOINTS.games, {}, this.config)
    return response.data
  }

  async join() {}

  async gamesPageLoader() {
    // seperated full loader includes a few requsts
    if (!this.auth) {
      return await this.getAll()
    }

    const played = await this.getPlayed()
    const other = await this.getOther()
    return { played, other }
  }

  async gameDetailLoader({ params }) {
    // seperated full loader includes a few requsts
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }

    let response = await axios.get(
      ENDPOINTS.gameDetail.replace(':gameId', params.gameId),
      this.config
    )
    const game = response.data

    response = await axios.get(
      ENDPOINTS.playersMe.replace(':gameId', params.gameId),
      this.config
    )
    const playerMe = response.data

    response = await axios.get(
      ENDPOINTS.playersOther.replace(':gameId', params.gameId),
      this.config
    )
    const playersOther = response.data

    response = await axios.get(
      ENDPOINTS.actions.replace(':gameId', params.gameId),
      this.config
    )
    const actions = response.data

    return { game, playerMe, playersOther, actions }
  }
}
