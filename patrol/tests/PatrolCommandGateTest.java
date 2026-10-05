import com.fsr.djibridge.PatrolCommandGate;

public final class PatrolCommandGateTest {
    static String session = "0123456789abcdef0123456789abcdef";
    static void expect(boolean result, boolean expected, String name) {
        if (result != expected) throw new AssertionError(name);
    }
    static boolean accepts(String token, String prev, long previous, long seq, long expires, double roll, double pitch, double yaw) {
        return PatrolCommandGate.accepts(1,"secret",token,prev,session,previous,seq,1000,expires,roll,pitch,0,yaw);
    }
    public static void main(String[] args) {
        expect(accepts("secret",null,0,1,1250,.1,.1,0),true,"valid");
        expect(accepts("wrong",null,0,1,1250,0,0,0),false,"authentication");
        expect(accepts("secret",null,0,1,1000,0,0,0),false,"expiry");
        expect(accepts("secret",null,0,1,1301,0,0,0),false,"future ttl");
        expect(accepts("secret",session,2,2,1250,0,0,0),false,"replay");
        expect(accepts("secret","different",0,1,1250,0,0,0),false,"session");
        expect(accepts("secret",null,0,1,1250,Double.NaN,0,0),false,"nan");
        expect(accepts("secret",null,0,1,1250,Double.POSITIVE_INFINITY,0,0),false,"infinity");
        expect(accepts("secret",null,0,1,1250,.2,.2,0),false,"speed norm");
        expect(accepts("secret",null,0,1,1250,0,0,11),false,"yaw bound");
        System.out.println("10 command gate checks passed");
    }
}
