import axios from "axios";
import autoBind from "auto-bind";

const urls = {
  login: "api/v1/auth/token/login/",
  logout: "api/v1/auth/token/logout/",
  me: "api/v1/auth/users/me/",
};

export default class AuthService {
  constructor(token = null) {
    this.token = token;
    autoBind(this);
  }

  get config() {
    return {
      headers: {
        Authorization: `Token ${this.token}`,
      },
    };
  }

  async login(username, password) {
    try {
      const response = await axios.post(urls.login, { username, password });
      this.token = response.data.auth_token;
      this.error = null;
    } catch (e) {
      if (e.code === "ERR_BAD_REQUEST") {
        this.error_message = e.response.data;
      } else {
        throw e;
      }
    }
  }

  async logout() {
    if (!this.token) {
      console.log("warning : AuthService.me() : No token provided. ");
      return null;
    }
    const response = await axios.post(urls.logout, this.token, this.config);
    this.token = null;
    return response.data;
  }

  async me() {
    if (!this.token) {
      console.log("warning : AuthService.me() : No token provided. ");
      return null;
    }

    const response = await axios.get(urls.me, this.config);
    return response.data;
  }

  // test_func() {
  //   console.log("test func with token: " + this.token);
  // }
}
