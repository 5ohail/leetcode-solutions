class Solution {
public:
    int addDigits(int num) {
        if(num <= 9){
            return num;
        }
        else{
            int dig = 0, rem;
            while(num !=0){
                rem = num % 10;
                dig = dig + rem;
                num = num/10;
            }
            return addDigits(dig);
        }
    }
};