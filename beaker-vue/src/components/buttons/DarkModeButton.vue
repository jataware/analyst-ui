<template>
    <Button
        text
        @click="props.toggleDarkMode"
        style="margin: 0; color: var(--gray-500);"
        :icon="themeIcon"
        v-tooltip.right="{value: 'Swap Theme', showDelay: 300}"
    />
</template>

<script setup>
import { defineProps, defineEmits, computed, inject } from "vue";
import Toolbar from 'primevue/toolbar';
import Button from 'primevue/button';


// TODO too many granular props- use a slot instead?
const props = defineProps([
    "toggleDarkMode",
]);

const theme = inject('theme');
const beakerSession = inject("beakerSession");

const themeIcon = computed(() => {
    return `pi pi-${theme === 'dark' ? 'sun' : 'moon'}`;
});


</script>