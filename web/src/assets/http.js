import axios from 'axios'

console.log('imoport', import.meta)
// 创建axios实例
export const http = axios.create({
    // baseURL: '/api',
    withCredentials: true, // send cookies when cross-domain requests
    // timeout: 10000, // request timeout //请求超时时间
})

// axios请求拦截器
http.interceptors.request.use((config) => {

    return config
}, (error) => {
    return Promise.reject(error)
})
// axios响应拦截器
http.interceptors.response.use(function (response) {

    try {
        response.data.resultMsg = JSON.parse(response.data.resultMsg)
    } catch (error) {
        // console.log('error=>\n', error);
    }

    return response.data;
}, (error) => {
    return Promise.reject(error);
});


//get
function get(url, data) {
    let config = { headers: { 'Content-Type': 'appliction/x-www-form-urlencoded' } };
    return http.get(url, { params: data }, config)
}
//post json
function post(url, data, config) {
    return http.post(url, data, config)
}

//post FormData
function postForm(url, data) {
    let config = { headers: { 'Content-Type': 'appliction/x-www-form-urlencoded' } };
    let params = new FormData();
    for (let i in data) {
        //数组
        if (Array.isArray(data[i])) {
            for (let j in data[i]) {
                params.append(`${i}[]`, data[i][j])
            }
        } else {
            params.append(i, data[i])
        }
    }
    return http.post(url, params, config)
}


let $http = function (params) {
    let { type = '', url, data, config } = params
    type = type.toLowerCase()
    if (type == 'get' && url !== '') {
        return get(url, data)
    }
    if (type == 'post' && url !== '') {
        return post(url, data, config)
    }
  
    if (type == 'postform' && url !== '') {
        return postForm(url, data)
    }
    return http(params)
}

$http.get = get
$http.post = post
$http.postForm = postForm

export default $http