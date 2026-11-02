class Solution {
public:
    bool possibleToDistr(int mid, vector<int>& quantities,int n){
        for(int &products : quantities){
            n -= (products + mid -1)/mid;
            if(n<0){
                return false;
            }
        }
        return true;
    }
    int minimizedMaximum(int n, vector<int>& quantities) {
        int y = quantities.size();
        int l = 1,r = *max_element(begin(quantities),end(quantities));
        int result = 0;
        while(l<=r){
            int mid = l + (r-l)/2;

            if(possibleToDistr(mid, quantities, n)){
                result = mid;
                r = mid - 1;
            }
            else{
                l = mid + 1;
            }
        }
        return result;
    }
};