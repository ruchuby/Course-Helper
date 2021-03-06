import {createRouter, createWebHashHistory} from 'vue-router'
import Login from "@/views/Login"
import CourseList from "@/views/CourseList"
import Course from "@/views/Course"
import HomeworkDetails from "@/views/HomeworkDetails"
import Download from "@/views/Download"

const routes = [
    {
        path: '/',
        name: 'login',
        component: Login
    },
    {
        path: '/courseList',
        name: 'courseList',
        component: CourseList
    },
    {
        path: '/course/:id?/:name?',
        name: 'course',
        component: Course,
    },
    {
        path: '/download',
        name: 'download',
        component: Download,
    },
    {
        path: '/homeworkDetails/:activeId?/:courseName?',
        name: 'homeworkDetails',
        component: HomeworkDetails,
    }
]

const router = createRouter({
    routes,
    history: createWebHashHistory()
})

// 暴露给api模块
window.$routerPush = router.push

export default router
