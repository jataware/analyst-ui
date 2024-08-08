<template>
    <div class="datasource-cell">
        <Card 
            v-for="source in cell.metadata.sources" 
            :key="source.name" 
            class="datasource"
        >
            <template #header>
                <img 
                    class="datasource-logo" 
                    alt="logo" 
                    :src="`data:image/png;base64,${source.logo}`" 
                />
            </template>
            <template #title>{{ source.name }}</template>
            <template #subtitle>
                <a class="datasource-link" :href="source.base_url">{{ source.base_url }}</a>
            </template>
            <template #content>
                <p class="m-0">
                    {{ source.purpose }}
                </p>
            </template>
        </Card>
    </div>
</template>

<script setup lang="ts">
import { defineProps, ref, inject, computed, nextTick, onBeforeMount, defineExpose, getCurrentInstance, onBeforeUnmount} from "vue";
import { BeakerSessionComponentType } from '@/components/session/BeakerSession.vue';
import Card from 'primevue/card';
import Button from 'primevue/button';

const props = defineProps([
    "cell",
]);

const instance = getCurrentInstance();
const beakerSession = inject<BeakerSessionComponentType>("beakerSession");
const cell = ref(props.cell);

// no-ops, read only cell
const no_op = () => {
    return;
}
const execute = no_op;
const enter = no_op;
const exit = no_op;
const clear = no_op;
defineExpose({
    execute,
    enter,
    exit,
    clear,
});

onBeforeMount(() => {
    beakerSession.cellRegistry[cell.value.id] = instance.vnode;
})

onBeforeUnmount(() => {
    delete beakerSession.cellRegistry[cell.value.id];
});

</script>

<script lang="ts">
import { BeakerRawCell } from "beaker-kernel";
export default {
    modelClass: BeakerRawCell
};
</script>

<style lang="scss" >

.datasource-cell {
    display: flex;
    flex-wrap: wrap;
}

.datasource {
    width: 16rem;
    height: 28rem;
    margin: 5px;
    overflow-y: scroll;
    overflow-x: hidden;
}

.datasource-logo {
    width: 100%;
    height: 60px;
    border-radius: 1rem;
}

.datasource-link[href] {
    text-overflow: ellipsis;
    overflow: hidden;
    max-width: 100%;
    display: inline-block;
    white-space: nowrap;
}

.datasource .p-card-body {
    display: flex;
    flex-direction: column;
    .p-card-title {
        font-size: 1.25rem;
    }
    .p-card-content {
        padding-top: 0rem;
        overflow-y: scroll;
        height: 100%;
    }
}

</style>
