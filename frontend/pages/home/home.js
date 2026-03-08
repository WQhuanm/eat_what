const app = getApp()

Page({
  onShow() {
    app.checkLogin()
  },
  startRecommend() {
    wx.navigateTo({ url: '/pages/questionnaire/questionnaire' })
  }
})
