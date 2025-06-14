import type {AxiosInstance} from 'axios';

export const attachAuthInterceptor = (client: AxiosInstance) => {
    client.interceptors.request.use(
        (config) => {
            const token = localStorage.getItem('access_token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            return config;
        },
        (error) => Promise.reject(error)
    );

    client.interceptors.response.use(
        (res) => res,
        (err) => {
            if (err.response?.status === 401) {
                console.warn('🔒 인증 만료. 재로그인 필요');
                // 예: location.href = '/login';
            }
            return Promise.reject(err);
        }
    );
};
