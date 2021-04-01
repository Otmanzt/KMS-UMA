#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <sys/time.h>
#include <smmintrin.h>

#define N 268435456

double gettime(void)
{
    struct timeval tv;
    gettimeofday(&tv,NULL);
    return tv.tv_sec + 1e-6*tv.tv_usec;
}

int main(int argc, char *argv[])
{
    float *r, *a, *b;
    float max = 0.0;
    int i;
    double dtime;

    r = (float *) malloc(N*sizeof(float *));
    posix_memalign((void *)&r[0], 16, N*sizeof(float *));
    a = (float *) malloc(N*sizeof(float *));
    posix_memalign((void *)&a[0], 16, N*sizeof(float *));
    b = (float *) malloc(N*sizeof(float *));
    posix_memalign((void *)&b[0], 16, N*sizeof(float *));

    for (i = 0; i < N; i++)
    {
       a[i] = (float) i;
       b[N-i-1] = (float) 2*i;
    }

    float cte = 0.5;
    __m128 cte128 = _mm_set1_ps(cte);
	
    dtime = gettime();

    for (i = 0; i < N; i+=4)
    {
       // r[i] = sqrtf(a[i]*a[i] + b[i]*b[i]) + 0.5;
       __m128 av = _mm_load_ps(&a[i]);
       __m128 bv = _mm_load_ps(&b[i]);
       __m128 sum = _mm_add_ps(_mm_mul_ps(av, av), _mm_mul_ps(bv, bv));
       __m128 res = _mm_add_ps(_mm_sqrt_ps(sum), cte128);
	   _mm_store_ps(&r[i], res);
       
	   // if (r[i] > max) max = r[i];
       __m128 maxv = _mm_set1_ps(max);
       if (_mm_comigt_ss(res, maxv)) _mm_store_ps(&max, res);
    }

    dtime = gettime() - dtime;

    printf("r: %f %f %f %f %f %f\n",r[0],r[1],r[2],r[3],r[1000],r[1001]);
    printf("max: %f\n",max);
    printf("Exec time: %9.5f sec.\n",dtime);
}