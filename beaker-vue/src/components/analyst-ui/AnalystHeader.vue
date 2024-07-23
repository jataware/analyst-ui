<template>
    <Toolbar class="toolbar">
        <template #start>
            <div>
            </div>
        </template>
        <template #center>
            <div class="logo">
                <h4>
                </h4>
            </div>
        </template>
        <template #end>
            <nav>
                <Button
                    text
                    @click="props.toggleDarkMode"
                    style="margin: 0; color: var(--gray-500);"
                    :icon="themeIcon"
                />
               <a
                    href="https://github.com/jataware/beaker-kernel"
                    rel="noopener"
                    target="_blank"
                >
                    <Button
                        text
                        style="margin: 0; color: var(--gray-500);"
                        aria-label="Github Repository Link Icon"
                        icon="pi pi-github"
                    />
                </a>
            </nav>
        </template>
    </Toolbar>
</template>

<script setup>
import { defineProps, defineEmits, computed, inject } from "vue";
import Toolbar from 'primevue/toolbar';
import Button from 'primevue/button';
import { capitalize } from '../../util';

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

<style lang="scss">

.toolbar {
    width: 100%;
    padding: 0.5rem 1rem;

    &.p-toolbar {
        flex-wrap: nowrap;
    }
    .p-toolbar-group-end {
        margin-left: -0.5rem;
    }

    .logo {
        font-size: 1.5rem;
        padding: 0 0.5rem;
        h4 {
            font-size: 1.8rem;
            margin: 0;
            padding: 0;
            font-weight: 500;
            color: var(--gray-500);

        }
    }

}

</style>