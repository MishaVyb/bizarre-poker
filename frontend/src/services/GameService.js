import axios from 'axios'
import autoBind from 'auto-bind'
import delay from '../utils/functools'

const ENDPOINTS = {
  games: '/api/v1/games/',
  gameDetail: '/api/v1/games/:gameId/',

  players: '/api/v1/games/:gameId/players/',
  playersDetail: '/api/v1/games/:gameId/players/:playerId',
  playersMe: '/api/v1/games/:gameId/players/me',
  playersOther: '/api/v1/games/:gameId/players/other',

  actions: '/api/v1/games/:gameId/actions/',
  forceContinue: '/api/v1/games/:gameId/actions/forceContinue/',  // mostly for test porpuses
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
    // for acting actions with POST request
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }
    const response = await axios.post(url, data, this.config)
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


  // tmp solution
  // this action should be provided by server with among other game actions with changing its stage
  async forceContinue(gameId, data = {}) {
    if (!this.token) {
      console.log('warning : No token provided. ')
      return null
    }
    const response = await axios.post(
      ENDPOINTS.forceContinue.replace(':gameId', gameId),
      data,
      this.config
    )
    return response.data
  }

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

    console.log('info : gameDetailLoader')
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
