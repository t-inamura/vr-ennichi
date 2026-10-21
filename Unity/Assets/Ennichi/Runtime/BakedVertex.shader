Shader "Ennichi/BakedVertex"
{
    Properties { _PreviewLighting ("Preview only",Float)=0 }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Pass
        {
            Cull Back
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            struct appdata {float4 vertex:POSITION;float3 normal:NORMAL;float4 color:COLOR;};
            struct v2f {float4 pos:SV_POSITION;float4 color:COLOR;float3 normal:TEXCOORD0;};
            float _PreviewLighting;
            v2f vert(appdata v){v2f o;o.pos=UnityObjectToClipPos(v.vertex);o.color=v.color;o.normal=UnityObjectToWorldNormal(v.normal);return o;}
            float4 frag(v2f i):SV_Target
            {
                float shade=lerp(1,.35+.65*max(0,dot(normalize(i.normal),normalize(float3(-.4,.8,-.3)))),_PreviewLighting);
                return float4(i.color.rgb*shade,1);
            }
            ENDCG
        }
    }
}
