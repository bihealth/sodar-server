<template>
  <span class="sodar-ss-notify-container align-middle mr-1">
    <transition name="fade" mode="out-in">
      <span v-if="notifyVisible"
            ref="notifyBadge"
            :class="notifyClasses">
        {{ notifyMessage }}
      </span>
    </transition>
  </span>
</template>

<script>

// TODO: Add notifications to queue, show sequentially

export default {
  name: 'NotifyBadge',
  data () {
    return {
      notifyVisible: false,
      notifyMessage: null,
      notifyClasses: 'badge badge-pill sodar-ss-notify-badge mx-2'
    }
  },
  methods: {
    show (message, variant, delay) {
      this.notifyClasses = 'badge badge-pill sodar-ss-notify-badge mx-2 badge-'

      if (variant) this.notifyClasses += variant
      else this.notifyClasses += 'light'

      this.notifyMessage = message
      this.notifyVisible = true

      setTimeout(() => {
        this.notifyVisible = false
        this.notifyMessage = null
      }, delay || 2000)
    }
  }
}
</script>

<style scoped>

span.sodar-ss-notify-container {
  display: inline-block;
  width: 150px;
  text-align: right;
  font-size: 16px !important;
  line-height: 16px;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity .3s;
}

.fade-enter, .fade-leave-to /* .fade-leave-active below version 2.1.8 */ {
  opacity: 0;
}

</style>
