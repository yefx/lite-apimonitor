<template>
  <div class="common-layout">
    <el-table class="" :data="state.list" stripe>
      <el-table-column v-for="(item, i) in tableColumns" :label="item">
        <template #default="scope">
          {{ scope.row[i] }}
        </template>
      </el-table-column>
      <el-table-column label="操作" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="handleEdit(scope.$index, scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.$index, scope.row)">删除</el-button>
          </template>
        </el-table-column>
    </el-table>
  </div>
</template>
<script setup>
import { reactive, onMounted } from 'vue'
import http from './assets/http'
const state = reactive({
  list: [],
  page: 1,
  pageSize: 10,
})

const tableColumns = ['任务名', '请求方式', '请求地址', '请求头', '请求参数', '响应时间', '预期响应状态码', '请求间隔时间', '关键字']



const getList = async () => {
  const res = await http({
    method: 'get',
    url: '/tasks'
  })

  console.log('res', res)
  if (res && res.tasks) {
    state.list = res.tasks;
  }
}

onMounted(() => {
  getList()
})
</script> 
<style lang="scss" scoped>
.common-layout {
  // background-color: #012;
  max-width: 1920px;
}
</style>