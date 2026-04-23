const app = getApp()

function request(url, method, data) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.baseUrl + url,
      method: method || 'GET',
      data: data,
      header: {
        'Content-Type': 'application/json',
        'Authorization': app.globalData.token ? 'Bearer ' + app.globalData.token : ''
      },
      success(res) {
        if (res.statusCode === 401) {
          wx.removeStorageSync('token')
          app.globalData.token = ''
          wx.reLaunch({ url: '/pages/login/login' })
          reject(new Error('未授权'))
          return
        }
        if (res.statusCode >= 400) {
          const msg = (res.data && res.data.detail) || '请求失败'
          reject(new Error(msg))
          return
        }
        resolve(res.data)
      },
      fail(err) {
        reject(err)
      }
    })
  })
}

module.exports = {
  // Auth
  register: (data) => request('/api/auth/register', 'POST', data),
  login: (data) => request('/api/auth/login', 'POST', data),

  // Profile
  getProfile: () => request('/api/profile', 'GET'),
  createProfile: (data) => request('/api/profile', 'POST', data),
  updateProfile: (data) => request('/api/profile', 'PUT', data),

  // Dish & Shop（路径修正）
  createDish: (data) => request('/api/dishes', 'POST', data),
  getDishes: (params) => request('/api/dishes' + (params ? '?' + params : ''), 'GET'),
  getDish: (id) => request('/api/dishes/' + id, 'GET'),
  createShop: (data) => request('/api/shops', 'POST', data),
  getShops: (city) => request('/api/shops' + (city ? '?city=' + city : ''), 'GET'),
  approveDish: (id) => request(`/api/dishes/${id}/approve`, 'PUT'),
  approveShop: (id) => request(`/api/shops/${id}/approve`, 'PUT'),
  
  // Recommend
  getQuestions: () => request('/api/recommend/questions', 'GET'),
  submitQuestionnaire: (data, lat, lng) =>
    request(`/api/recommend/submit?latitude=${lat || 0}&longitude=${lng || 0}`, 'POST', data),
  confirmSelection: (data) => request('/api/recommend/confirm', 'POST', data),
  logInteraction: (data) => request('/api/recommend/interaction', 'POST', data),

  // History
  getHistory: (skip, limit) => request(`/api/history?skip=${skip || 0}&limit=${limit || 20}`, 'GET'),
  getHistoryDetail: (id) => request(`/api/history/${id}`, 'GET'),

  // Nearby
  getNearbyDishes: (lat, lng, radius_km = 5, limit = 30, skip = 0) =>
    request(`/api/recommend/nearby?latitude=${lat}&longitude=${lng}&radius_km=${radius_km}&limit=${limit}&skip=${skip}`, 'GET'),
}
