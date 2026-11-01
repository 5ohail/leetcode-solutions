class Solution {
public:
    int mySqrt(int x) {
        int i = 1, j = x;
        if(x<2) return x;
        int sq = 1;
        while(i<=j){
            int mid = i + (j-i)/2;
            if(1LL * mid * mid == x) return mid;
            else if(1LL * mid * mid < x){
                sq = mid;
                i = mid + 1;
            }
            else if(1LL * mid * mid > x){
                j = mid - 1;
            }
        }
        return sq;
    }
};