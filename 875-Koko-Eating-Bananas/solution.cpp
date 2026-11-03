class Solution {
public:
    bool eatBananas(int mid, vector<int> piles,int h){
        int check = 0;
        for(int x : piles){
            check += x/mid;
            if(x % mid != 0){
                check++;
            }
        }
        return check <= h;
    }
    int minEatingSpeed(vector<int>& piles, int h) {
        int left = 1, right = *max_element(begin(piles),end(piles));
        while(left < right){
            int mid = left + (right-left)/2;
            if(eatBananas(mid,piles,h)){
                right = mid;
            }
            else{
                left = mid+1;
            }
        }
        return left;
    }
};