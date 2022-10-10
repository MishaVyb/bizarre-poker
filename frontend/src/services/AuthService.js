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

  static async logout(token) {
    const config = {
      headers: {
        Authorization: `Token ${token}`,
      },
    };
    const response = await axios.post(urls.logout, token, config);
    return response.data;
  }

  async me() {
    console.log("get me with: ", { ...this });

    const config = {
      headers: {
        Authorization: `Token ${this.token}`,
      },
    };
    const response = await axios.get(urls.me, config);
    return response.data;
  }

  test_func() {
    console.log("test func with token: " + this.token);
  }
}
