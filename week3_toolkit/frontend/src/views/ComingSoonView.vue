<template>
  <section class="coming-card">
    <div class="coming-icon">{{ icon }}</div>
    <p class="eyebrow">{{ eyebrow }}</p>
    <h2>{{ title }}</h2>
    <p class="description">{{ description }}</p>

    <ul>
      <li v-for="item in items" :key="item">{{ item }}</li>
    </ul>
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    description: string
    eyebrow?: string
    icon?: string
    items?: string[]
  }>(),
  {
    eyebrow: '下一阶段',
    icon: '✦',
    items: () => [],
  },
)
</script>

<style scoped>
.coming-card {
  width: min(620px, 100%);
  margin: 0 auto;
  padding: 42px;
  box-sizing: border-box;
  text-align: center;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(255, 255, 255, 0.86);
  border-radius: 30px;
  box-shadow: 0 22px 55px rgba(125, 90, 80, 0.1);
  backdrop-filter: blur(20px);
}

.coming-icon {
  width: 70px;
  height: 70px;
  display: grid;
  place-items: center;
  margin: 0 auto 18px;
  border-radius: 23px;
  background: linear-gradient(135deg, #ffd7dc, #d6f1e7);
  color: #5d4037;
  font-size: 34px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #b07f8a;
  font-size: 13px;
  letter-spacing: 0.18em;
}

h2 {
  margin: 0 0 14px;
  color: #5d4037;
  font-size: 28px;
}

.description {
  margin: 0 auto;
  max-width: 480px;
  color: #8d746a;
  line-height: 1.8;
}

ul {
  display: grid;
  gap: 9px;
  max-width: 390px;
  margin: 24px auto 0;
  padding: 0;
  list-style: none;
  text-align: left;
}

li {
  padding: 10px 14px;
  border-radius: 12px;
  color: #6d4c41;
  background: rgba(248, 187, 208, 0.12);
}

@media (max-width: 560px) {
  .coming-card {
    padding: 30px 20px;
    border-radius: 24px;
  }

  h2 {
    font-size: 23px;
  }
}
</style>
