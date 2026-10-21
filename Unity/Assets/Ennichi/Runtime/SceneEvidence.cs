using UnityEngine;
namespace Ennichi.Unity
{
    public sealed class SceneEvidence : ScriptableObject
    {
        public string sourceSha256,derivedSha256,appearance,blenderVersion,reviewNotes;
        public bool visualApproved;
    }
}
